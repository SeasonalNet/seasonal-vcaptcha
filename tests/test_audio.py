import wave

import pytest

from seasonal_vcaptcha.audio import AudioConfig, AudioInputError, prepare_audio


def make_wav(path, *, channels=1, sample_width=2, sample_rate=16000, frames=b"\0\0" * 160):
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(sample_width)
        handle.setframerate(sample_rate)
        handle.writeframes(frames)


def test_prepare_audio_accepts_compatible_wav(tmp_path):
    path = tmp_path / "ok.wav"
    make_wav(path)

    prepared = prepare_audio(str(path), AudioConfig(temp_dir=str(tmp_path)))

    assert prepared.path == str(path)
    assert prepared.converted is False
    assert prepared.cleanup_path is None


def test_prepare_audio_rejects_missing_file(tmp_path):
    with pytest.raises(AudioInputError):
        prepare_audio(str(tmp_path / "missing.wav"), AudioConfig(temp_dir=str(tmp_path)))
