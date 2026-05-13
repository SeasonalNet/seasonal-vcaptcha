"""Audio normalization helpers for Vosk recognition."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave


class AudioError(RuntimeError):
    """Base class for audio preparation failures."""


class AudioInputError(AudioError):
    """The supplied audio path is missing or unreadable."""


class AudioConversionError(AudioError):
    """The supplied audio could not be converted to recognizer-safe WAV."""


@dataclass(frozen=True)
class AudioConfig:
    sox_path: str = "/usr/bin/sox"
    target_sample_rate: int = 16000
    target_channels: int = 1
    target_bits: int = 16
    max_duration_seconds: float = 10.0
    temp_dir: str | None = None
    cleanup_temp_files: bool = True


@dataclass(frozen=True)
class PreparedAudio:
    path: str
    converted: bool
    duration_seconds: float | None = None
    cleanup_path: str | None = None


def _probe_wav(path: str) -> tuple[int, int, int, int, float | None]:
    with wave.open(path, "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        duration = None
        if sample_rate > 0:
            duration = frame_count / float(sample_rate)
        return channels, sample_width, sample_rate, frame_count, duration


def _check_duration(duration: float | None, max_duration_seconds: float | None) -> None:
    if duration is None or max_duration_seconds is None or max_duration_seconds <= 0:
        return
    if duration > max_duration_seconds:
        raise AudioInputError(
            f"audio duration {duration:.2f}s exceeds limit {max_duration_seconds:.2f}s"
        )


def _is_compatible_wav(path: str, config: AudioConfig) -> tuple[bool, float | None]:
    try:
        channels, sample_width, sample_rate, _frame_count, duration = _probe_wav(path)
    except (wave.Error, EOFError, OSError):
        return False, None

    _check_duration(duration, config.max_duration_seconds)
    accepted_sample_rates = {config.target_sample_rate, 8000, 16000}
    ok = (
        channels == config.target_channels
        and sample_width == config.target_bits // 8
        and sample_rate in accepted_sample_rates
    )
    return ok, duration


def prepare_audio(path: str, config: AudioConfig) -> PreparedAudio:
    """Return a recognizer-safe WAV path, converting with sox when required.

    Conversion output is placed in a temporary file instead of next to the input,
    which avoids stale artifacts and concurrent call collisions.
    """

    source = Path(path)
    if not source.is_file():
        raise AudioInputError(f"input audio file does not exist: {path}")
    if not source.stat().st_size:
        raise AudioInputError(f"input audio file is empty: {path}")

    compatible, duration = _is_compatible_wav(str(source), config)
    if compatible:
        return PreparedAudio(path=str(source), converted=False, duration_seconds=duration)

    sox_path = shutil.which(config.sox_path) if "/" not in config.sox_path else config.sox_path
    if sox_path is None or not Path(sox_path).exists():
        raise AudioConversionError(f"sox executable not found: {config.sox_path}")

    temp_parent = config.temp_dir
    if temp_parent is not None:
        Path(temp_parent).mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        prefix="seasonal-vcaptcha-",
        suffix=".wav",
        dir=temp_parent,
        delete=False,
    ) as temp_file:
        temp_path = temp_file.name

    command = [
        sox_path,
        str(source),
        "-r",
        str(config.target_sample_rate),
        "-c",
        str(config.target_channels),
        "-b",
        str(config.target_bits),
        temp_path,
    ]

    try:
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True, text=True)
        _channels, _sample_width, _sample_rate, _frame_count, converted_duration = _probe_wav(temp_path)
        _check_duration(converted_duration, config.max_duration_seconds)
    except subprocess.CalledProcessError as exc:
        Path(temp_path).unlink(missing_ok=True)
        detail = (exc.stderr or "").strip()
        raise AudioConversionError(f"sox conversion failed: {detail or exc}") from exc
    except (wave.Error, EOFError, OSError, AudioInputError) as exc:
        Path(temp_path).unlink(missing_ok=True)
        raise AudioConversionError(f"converted audio is not usable: {exc}") from exc

    return PreparedAudio(
        path=temp_path,
        converted=True,
        duration_seconds=converted_duration,
        cleanup_path=temp_path if config.cleanup_temp_files else None,
    )
