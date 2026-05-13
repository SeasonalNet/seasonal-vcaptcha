from pathlib import Path

from seasonal_vcaptcha import cli
from seasonal_vcaptcha.protocol import ok_response


class FakeRecognizer:
    @classmethod
    def from_config(cls, config):
        return cls()

    def recognize_file(self, path, *, source):
        return ok_response(
            digits="1234",
            text="one two three four",
            duration_ms=10,
            audio_duration_ms=1000,
            converted=False,
            source=source,
        )


def test_cli_default_stdout_is_digits_only(monkeypatch, tmp_path, capsys):
    wav = tmp_path / "captcha.wav"
    wav.write_bytes(b"not really wav; recognizer is mocked")
    monkeypatch.setattr(cli, "VoskRecognizer", FakeRecognizer)

    exit_code = cli.main(["--mode", "direct", str(wav)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == "1234\n"
    assert "ok=true" in captured.err


def test_cli_json_format(monkeypatch, tmp_path, capsys):
    wav = tmp_path / "captcha.wav"
    wav.write_bytes(b"mock")
    monkeypatch.setattr(cli, "VoskRecognizer", FakeRecognizer)

    exit_code = cli.main(["--mode", "direct", "--format", "json", str(wav)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"digits":"1234"' in captured.out


def test_cli_missing_file_exits_input_error(capsys):
    exit_code = cli.main(["--mode", "direct", "/tmp/no-such-vcaptcha-file.wav"])

    captured = capsys.readouterr()
    assert exit_code == cli.EXIT_INPUT
    assert captured.out == ""
    assert "input file not found" in captured.err
