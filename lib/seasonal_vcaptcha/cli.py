"""Command-line interface used by Asterisk and operators."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .client import DaemonUnavailable, recognize_via_unix_socket
from .config import load_config
from .protocol import RecognizeResponse, error_response
from . import __version__
from .recognizer import VoskRecognizer

MODE_CHOICES = ("auto", "daemon", "direct")
FORMAT_CHOICES = ("digits", "json", "env")

EXIT_USAGE = 2
EXIT_INPUT = 3
EXIT_DAEMON_UNAVAILABLE = 4
EXIT_RECOGNITION_FAILED = 5
EXIT_DIRECT_FAILED = 6


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="seasonal-vcaptcha-digits",
        description="Recognize spoken CAPTCHA digits from a WAV file.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("wav_path", help="path to the recorded WAV file")
    parser.add_argument("--config", help="path to config.yaml")
    parser.add_argument("--mode", choices=MODE_CHOICES, help="recognition mode")
    parser.add_argument("--format", choices=FORMAT_CHOICES, help="stdout format")
    parser.add_argument("--socket-path", help="daemon Unix socket path")
    parser.add_argument("--timeout-seconds", type=float, help="daemon request timeout")
    return parser


def _format_env(response: RecognizeResponse) -> str:
    lines = [
        f"OK={1 if response.ok else 0}",
        f"DIGITS={response.digits}",
        f"SOURCE={response.source}",
    ]
    if response.duration_ms is not None:
        lines.append(f"DURATION_MS={response.duration_ms}")
    if response.audio_duration_ms is not None:
        lines.append(f"AUDIO_DURATION_MS={response.audio_duration_ms}")
    lines.append(f"CONVERTED={1 if response.converted else 0}")
    if not response.ok:
        lines.append(f"ERROR_CODE={response.error_code or 'recognition_failed'}")
        lines.append(f"ERROR_MESSAGE={response.error_message or 'recognition failed'}")
    return "\n".join(lines)


def format_response(response: RecognizeResponse, output_format: str) -> str:
    if output_format == "json":
        return response.to_json()
    if output_format == "env":
        return _format_env(response)
    return response.digits


def print_diagnostics(response: RecognizeResponse, *, stream) -> None:
    fields = [
        f"ok={str(response.ok).lower()}",
        f"source={response.source}",
        f"digits_len={len(response.digits)}",
        f"converted={str(response.converted).lower()}",
    ]
    if response.duration_ms is not None:
        fields.append(f"duration_ms={response.duration_ms}")
    if not response.ok:
        fields.append(f"error_code={response.error_code or 'recognition_failed'}")
    print(" ".join(fields), file=stream)


def run_direct(config: dict, wav_path: str) -> RecognizeResponse:
    recognizer = VoskRecognizer.from_config(config)
    return recognizer.recognize_file(wav_path, source="direct")


def run_daemon(config: dict, wav_path: str, socket_path: str | None, timeout_seconds: float | None) -> RecognizeResponse:
    cli_config = config.get("cli", {})
    return recognize_via_unix_socket(
        socket_path=socket_path or str(cli_config.get("socket_path")),
        wav_path=wav_path,
        timeout_seconds=float(timeout_seconds or cli_config.get("timeout_seconds", 6)),
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_path = Path(args.wav_path)
    if not input_path.is_file():
        print(f"input file not found: {input_path}", file=sys.stderr)
        return EXIT_INPUT

    try:
        config = load_config(args.config)
    except Exception as exc:
        print(f"failed to load config: {exc}", file=sys.stderr)
        return EXIT_USAGE

    cli_config = config.get("cli", {})
    mode = args.mode or str(cli_config.get("mode", "auto"))
    output_format = args.format or str(cli_config.get("format", "digits"))
    diagnostics_to_stderr = bool(cli_config.get("diagnostics_to_stderr", True))

    if mode not in MODE_CHOICES:
        print(f"invalid mode: {mode}", file=sys.stderr)
        return EXIT_USAGE
    if output_format not in FORMAT_CHOICES:
        print(f"invalid format: {output_format}", file=sys.stderr)
        return EXIT_USAGE

    daemon_error: DaemonUnavailable | None = None
    response: RecognizeResponse

    if mode in {"auto", "daemon"}:
        try:
            response = run_daemon(config, str(input_path), args.socket_path, args.timeout_seconds)
        except DaemonUnavailable as exc:
            daemon_error = exc
            if mode == "daemon":
                response = error_response("daemon_unavailable", str(exc), source="daemon")
                print(format_response(response, output_format))
                if diagnostics_to_stderr:
                    print_diagnostics(response, stream=sys.stderr)
                return EXIT_DAEMON_UNAVAILABLE
        else:
            print(format_response(response, output_format))
            if diagnostics_to_stderr:
                print_diagnostics(response, stream=sys.stderr)
            return 0 if response.ok else EXIT_RECOGNITION_FAILED

    response = run_direct(config, str(input_path))
    if daemon_error:
        response = RecognizeResponse.from_dict({**response.to_dict(), "source": "direct-fallback"})
    print(format_response(response, output_format))
    if diagnostics_to_stderr:
        print_diagnostics(response, stream=sys.stderr)
    return 0 if response.ok else EXIT_DIRECT_FAILED


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
