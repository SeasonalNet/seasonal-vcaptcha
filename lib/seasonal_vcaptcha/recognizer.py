"""Vosk-backed recognizer implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import time
import wave

from .audio import AudioConfig, AudioError, prepare_audio
from .digits import DEFAULT_DIGIT_ALIASES, DEFAULT_GRAMMAR_PHRASES, grammar_from_phrases, words_to_digits
from .protocol import RecognizeResponse, error_response, ok_response


@dataclass(frozen=True)
class RecognizerConfig:
    model_path: str
    sample_rate: int = 16000
    grammar_enabled: bool = True
    grammar_phrases: tuple[str, ...] = DEFAULT_GRAMMAR_PHRASES
    digit_aliases: dict[str, str] | None = None
    min_digits: int = 1
    max_digits: int = 8
    allow_empty_result: bool = True


class VoskRecognizer:
    """Reusable recognizer that keeps the Vosk model loaded in memory."""

    def __init__(self, recognizer_config: RecognizerConfig, audio_config: AudioConfig) -> None:
        self.recognizer_config = recognizer_config
        self.audio_config = audio_config
        self._model = None

    @classmethod
    def from_config(cls, config: dict) -> "VoskRecognizer":
        vosk_cfg = config["recognizer"]["vosk"]
        grammar_cfg = vosk_cfg.get("grammar", {})
        audio_cfg = config.get("audio", {})
        recognition_cfg = config.get("recognition", {})
        service_cfg = config.get("service", {})

        return cls(
            RecognizerConfig(
                model_path=str(vosk_cfg["model_path"]),
                sample_rate=int(vosk_cfg.get("sample_rate", 16000)),
                grammar_enabled=bool(grammar_cfg.get("enabled", True)),
                grammar_phrases=tuple(grammar_cfg.get("phrases") or DEFAULT_GRAMMAR_PHRASES),
                digit_aliases=dict(recognition_cfg.get("digit_aliases") or DEFAULT_DIGIT_ALIASES),
                min_digits=int(recognition_cfg.get("min_digits", 1)),
                max_digits=int(recognition_cfg.get("max_digits", 8)),
                allow_empty_result=bool(recognition_cfg.get("allow_empty_result", True)),
            ),
            AudioConfig(
                sox_path=str(audio_cfg.get("sox_path", "/usr/bin/sox")),
                target_sample_rate=int(audio_cfg.get("target_sample_rate", 16000)),
                target_channels=int(audio_cfg.get("target_channels", 1)),
                target_bits=int(audio_cfg.get("target_bits", 16)),
                max_duration_seconds=float(audio_cfg.get("max_duration_seconds", 10)),
                temp_dir=str(service_cfg.get("temp_dir")) if service_cfg.get("temp_dir") else None,
                cleanup_temp_files=bool(audio_cfg.get("cleanup_temp_files", True)),
            ),
        )

    def load(self) -> None:
        """Load the Vosk model if it is not already resident."""

        if self._model is not None:
            return

        model_path = Path(self.recognizer_config.model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Vosk model path does not exist: {model_path}")

        from vosk import Model, SetLogLevel

        SetLogLevel(-1)
        self._model = Model(str(model_path))

    def recognize_file(self, path: str, *, source: str = "direct") -> RecognizeResponse:
        started = time.monotonic()
        prepared = None
        raw_text_parts: list[str] = []

        try:
            self.load()
            prepared = prepare_audio(path, self.audio_config)

            from vosk import KaldiRecognizer

            with wave.open(prepared.path, "rb") as wav_file:
                grammar = None
                if self.recognizer_config.grammar_enabled:
                    grammar = grammar_from_phrases(self.recognizer_config.grammar_phrases)

                if grammar:
                    recognizer = KaldiRecognizer(self._model, wav_file.getframerate(), grammar)
                else:
                    recognizer = KaldiRecognizer(self._model, wav_file.getframerate())
                recognizer.SetWords(False)

                while True:
                    data = wav_file.readframes(4000)
                    if not data:
                        break
                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        raw_text_parts.append(result.get("text", ""))

                final_result = json.loads(recognizer.FinalResult())
                raw_text_parts.append(final_result.get("text", ""))

            text = " ".join(part for part in raw_text_parts if part).strip()
            digits = words_to_digits(
                text,
                aliases=self.recognizer_config.digit_aliases,
                max_digits=self.recognizer_config.max_digits,
            )
            if not digits and not self.recognizer_config.allow_empty_result:
                return error_response("no_digits", "no digits recognized", source=source)
            if digits and len(digits) < self.recognizer_config.min_digits:
                return error_response("too_few_digits", "recognized fewer digits than required", source=source)

            duration_ms = int((time.monotonic() - started) * 1000)
            audio_duration_ms = None
            if prepared.duration_seconds is not None:
                audio_duration_ms = int(prepared.duration_seconds * 1000)
            return ok_response(
                digits=digits,
                text=text,
                duration_ms=duration_ms,
                audio_duration_ms=audio_duration_ms,
                converted=prepared.converted,
                source=source,
            )
        except FileNotFoundError as exc:
            return error_response("model_missing", str(exc), source=source)
        except AudioError as exc:
            return error_response("audio_error", str(exc), source=source)
        except Exception as exc:  # pragma: no cover - defensive boundary around Vosk/runtime
            return error_response("recognition_failed", str(exc), source=source)
        finally:
            if prepared and prepared.cleanup_path:
                Path(prepared.cleanup_path).unlink(missing_ok=True)
