"""Request/response protocol shared by the CLI and daemon."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import json


@dataclass(frozen=True)
class RecognizeRequest:
    path: str

    @classmethod
    def from_json(cls, payload: bytes | str) -> "RecognizeRequest":
        raw = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        data = json.loads(raw)
        path = str(data.get("path", ""))
        if not path:
            raise ValueError("missing required field: path")
        return cls(path=path)

    def to_json_bytes(self) -> bytes:
        return json.dumps({"path": self.path}, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class RecognizeResponse:
    ok: bool
    digits: str = ""
    text: str = ""
    duration_ms: int | None = None
    audio_duration_ms: int | None = None
    converted: bool = False
    source: str = "daemon"
    error_code: str | None = None
    error_message: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "ok": self.ok,
            "digits": self.digits,
            "text": self.text,
            "duration_ms": self.duration_ms,
            "audio_duration_ms": self.audio_duration_ms,
            "converted": self.converted,
            "source": self.source,
        }
        if not self.ok:
            data["error"] = {
                "code": self.error_code or "recognition_failed",
                "message": self.error_message or "recognition failed",
            }
        data.update(self.extra)
        return {key: value for key, value in data.items() if value is not None}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)

    def to_json_bytes(self) -> bytes:
        return self.to_json().encode("utf-8")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecognizeResponse":
        error = data.get("error") or {}
        known_keys = {
            "ok",
            "digits",
            "text",
            "duration_ms",
            "audio_duration_ms",
            "converted",
            "source",
            "error",
        }
        return cls(
            ok=bool(data.get("ok", False)),
            digits=str(data.get("digits", "")),
            text=str(data.get("text", "")),
            duration_ms=data.get("duration_ms"),
            audio_duration_ms=data.get("audio_duration_ms"),
            converted=bool(data.get("converted", False)),
            source=str(data.get("source", "daemon")),
            error_code=error.get("code"),
            error_message=error.get("message"),
            extra={key: value for key, value in data.items() if key not in known_keys},
        )

    @classmethod
    def from_json(cls, payload: bytes | str) -> "RecognizeResponse":
        raw = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        return cls.from_dict(json.loads(raw))


def ok_response(
    *,
    digits: str,
    text: str,
    duration_ms: int,
    audio_duration_ms: int | None,
    converted: bool,
    source: str,
) -> RecognizeResponse:
    return RecognizeResponse(
        ok=True,
        digits=digits,
        text=text,
        duration_ms=duration_ms,
        audio_duration_ms=audio_duration_ms,
        converted=converted,
        source=source,
    )


def error_response(code: str, message: str, *, source: str = "daemon") -> RecognizeResponse:
    return RecognizeResponse(ok=False, error_code=code, error_message=message, source=source)
