"""Local daemon client helpers."""

from __future__ import annotations

import http.client
import socket

from .protocol import RecognizeRequest, RecognizeResponse


class DaemonUnavailable(RuntimeError):
    """The local daemon could not be reached."""


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: str, timeout: float) -> None:
        super().__init__("localhost", timeout=timeout)
        self.socket_path = socket_path

    def connect(self) -> None:  # pragma: no cover - exercised through integration/system use
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self.socket_path)
        self.sock = sock


def recognize_via_unix_socket(
    *,
    socket_path: str,
    wav_path: str,
    timeout_seconds: float,
) -> RecognizeResponse:
    request = RecognizeRequest(path=wav_path)
    connection = UnixHTTPConnection(socket_path, timeout_seconds)
    try:
        connection.request(
            "POST",
            "/v1/recognize",
            body=request.to_json_bytes(),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        payload = response.read()
        try:
            return RecognizeResponse.from_json(payload)
        except Exception as exc:
            if response.status >= 500:
                raise DaemonUnavailable(f"daemon returned HTTP {response.status}") from exc
            raise DaemonUnavailable(f"invalid daemon response: {exc}") from exc
    except (OSError, TimeoutError, http.client.HTTPException) as exc:
        raise DaemonUnavailable(str(exc)) from exc
    finally:
        connection.close()
