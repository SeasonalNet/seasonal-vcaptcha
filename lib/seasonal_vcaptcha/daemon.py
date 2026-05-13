"""Small local API daemon for warm Vosk recognition."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socketserver
from pathlib import Path
import argparse
import grp
import json
import logging
import os
import socket
import sys
import threading
import time

from .config import load_config
from .protocol import RecognizeRequest, error_response
from .recognizer import VoskRecognizer

LOGGER = logging.getLogger("seasonal_vcaptcha.daemon")


class UnixThreadingHTTPServer(ThreadingHTTPServer):
    """Threading HTTP server bound to a Unix domain socket."""

    address_family = socket.AF_UNIX

    def __init__(
        self,
        socket_path: str,
        handler_class,
        *,
        socket_mode: str = "0660",
        socket_group: str | None = None,
    ) -> None:
        self.socket_path = socket_path
        self.socket_mode = socket_mode
        self.socket_group = socket_group
        Path(socket_path).parent.mkdir(parents=True, exist_ok=True)
        Path(socket_path).unlink(missing_ok=True)
        super().__init__(socket_path, handler_class)

    def server_bind(self) -> None:  # pragma: no cover - system integration behavior
        socketserver.TCPServer.server_bind(self)
        self.server_name = "localhost"
        self.server_port = 0
        try:
            os.chmod(self.socket_path, int(str(self.socket_mode), 8))
        except OSError as exc:
            LOGGER.warning("failed to chmod socket %s: %s", self.socket_path, exc)
        if self.socket_group:
            try:
                gid = grp.getgrnam(self.socket_group).gr_gid
                os.chown(self.socket_path, -1, gid)
            except (KeyError, OSError) as exc:
                LOGGER.warning("failed to set socket group %s on %s: %s", self.socket_group, self.socket_path, exc)

    def server_close(self) -> None:  # pragma: no cover - system integration behavior
        super().server_close()
        Path(self.socket_path).unlink(missing_ok=True)


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def make_handler(
    *,
    recognizer: VoskRecognizer,
    max_body_bytes: int,
    max_concurrent_requests: int,
    metrics_enabled: bool,
    metrics_path: str,
):
    semaphore = threading.BoundedSemaphore(max(1, max_concurrent_requests))
    counters = {
        "requests_total": 0,
        "failures_total": 0,
        "busy_total": 0,
        "total_duration_ms": 0,
    }
    counters_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        server_version = "seasonal-vcaptcha/0.2"

        def address_string(self) -> str:
            # BaseHTTPRequestHandler assumes TCP client addresses are tuples.
            # Unix-domain HTTP handlers can receive an empty/string client
            # address, so make access logging safe for the production socket
            # transport.
            client_address = getattr(self, "client_address", None)
            if isinstance(client_address, tuple) and client_address:
                return str(client_address[0])
            if isinstance(client_address, str) and client_address:
                return client_address
            return "local"

        def log_message(self, fmt: str, *args) -> None:  # noqa: A003 - stdlib API name
            LOGGER.info("%s - %s", self.address_string(), fmt % args)

        def _send(self, status: int, body: bytes, content_type: str = "application/json") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, status: int, payload: dict) -> None:
            self._send(status, _json_bytes(payload))

        def do_GET(self) -> None:  # noqa: N802 - stdlib API name
            if self.path == "/healthz":
                self._send_json(200, {"ok": True, "service": "seasonal-vcaptcha"})
                return
            if self.path == "/readyz":
                # The daemon loads the model before serving. If we are handling
                # requests, readiness is true.
                self._send_json(200, {"ok": True, "ready": True})
                return
            if metrics_enabled and self.path == metrics_path:
                with counters_lock:
                    body = (
                        f"seasonal_vcaptcha_requests_total {counters['requests_total']}\n"
                        f"seasonal_vcaptcha_failures_total {counters['failures_total']}\n"
                        f"seasonal_vcaptcha_busy_total {counters['busy_total']}\n"
                        f"seasonal_vcaptcha_recognition_duration_ms_total {counters['total_duration_ms']}\n"
                    ).encode("utf-8")
                self._send(200, body, "text/plain; version=0.0.4")
                return
            self._send_json(404, {"ok": False, "error": {"code": "not_found", "message": "not found"}})

        def do_POST(self) -> None:  # noqa: N802 - stdlib API name
            if self.path != "/v1/recognize":
                self._send_json(404, {"ok": False, "error": {"code": "not_found", "message": "not found"}})
                return

            content_length = int(self.headers.get("Content-Length", "0") or "0")
            if content_length <= 0 or content_length > max_body_bytes:
                response = error_response("bad_request", "invalid request body size", source="daemon")
                self._send(400, response.to_json_bytes())
                return

            if not semaphore.acquire(blocking=False):
                with counters_lock:
                    counters["busy_total"] += 1
                response = error_response("busy", "recognizer is busy", source="daemon")
                self._send(503, response.to_json_bytes())
                return

            started = time.monotonic()
            try:
                payload = self.rfile.read(content_length)
                request = RecognizeRequest.from_json(payload)
                response = recognizer.recognize_file(request.path, source="daemon")
                duration_ms = response.duration_ms
                if duration_ms is None:
                    duration_ms = int((time.monotonic() - started) * 1000)

                with counters_lock:
                    counters["requests_total"] += 1
                    counters["total_duration_ms"] += duration_ms
                    if not response.ok:
                        counters["failures_total"] += 1

                self._send(200 if response.ok else 422, response.to_json_bytes())
            except Exception as exc:  # pragma: no cover - defensive HTTP boundary
                with counters_lock:
                    counters["requests_total"] += 1
                    counters["failures_total"] += 1
                response = error_response("request_failed", str(exc), source="daemon")
                self._send(400, response.to_json_bytes())
            finally:
                semaphore.release()

    return Handler


def configure_logging(config: dict) -> None:
    logging_cfg = config.get("logging", {})
    level_name = str(logging_cfg.get("level", "info")).upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="seasonal-vcaptcha-daemon",
        description="Run the Seasonal VCaptcha local recognition API daemon.",
    )
    parser.add_argument("--config", help="path to config.yaml")
    return parser


def serve(config: dict) -> int:
    api_config = config.get("api", {})
    if not api_config.get("enabled", True):
        LOGGER.error("api.enabled is false; nothing to serve")
        return 2

    recognizer = VoskRecognizer.from_config(config)
    LOGGER.info("loading recognizer model")
    recognizer.load()
    LOGGER.info("recognizer ready")

    handler = make_handler(
        recognizer=recognizer,
        max_body_bytes=int(api_config.get("max_body_bytes", 10 * 1024 * 1024)),
        max_concurrent_requests=int(api_config.get("max_concurrent_requests", 1)),
        metrics_enabled=bool(config.get("metrics", {}).get("enabled", False)),
        metrics_path=str(config.get("metrics", {}).get("path", "/metrics")),
    )

    unix_socket = api_config.get("unix_socket", {})
    tcp = api_config.get("tcp", {})

    if unix_socket.get("enabled", True):
        socket_path = str(unix_socket.get("path", "/run/seasonal-vcaptcha/seasonal-vcaptcha.sock"))
        socket_mode = str(unix_socket.get("mode", "0660"))
        socket_group = unix_socket.get("group")
        server = UnixThreadingHTTPServer(
            socket_path,
            handler,
            socket_mode=socket_mode,
            socket_group=str(socket_group) if socket_group else None,
        )
        LOGGER.info("serving on unix socket %s", socket_path)
    elif tcp.get("enabled", False):
        bind = str(tcp.get("bind", "127.0.0.1"))
        port = int(tcp.get("port", 8765))
        server = ThreadingHTTPServer((bind, port), handler)
        LOGGER.info("serving on tcp %s:%s", bind, port)
    else:
        LOGGER.error("no listener enabled; enable api.unix_socket or api.tcp")
        return 2

    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - operator behavior
        LOGGER.info("shutdown requested")
    finally:
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        configure_logging(config)
        return serve(config)
    except Exception as exc:
        print(f"seasonal-vcaptcha-daemon failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
