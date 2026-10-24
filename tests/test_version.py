from __future__ import annotations

import re

import pytest

from seasonal_vcaptcha import __version__
from seasonal_vcaptcha.cli import main as cli_main
from seasonal_vcaptcha.daemon import build_parser


def test_package_version_uses_git_derived_project_metadata() -> None:
    assert __version__ != "0.2.0"
    assert re.fullmatch(
        r"\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?(?:\.post\d+)?(?:\.dev\d+)?(?:\+[-.a-zA-Z0-9]+)?",
        __version__,
    )


def test_digit_cli_exposes_resolved_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        cli_main(["--version"])
    assert error.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_daemon_parser_exposes_resolved_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        build_parser().parse_args(["--version"])
    assert error.value.code == 0
    assert __version__ in capsys.readouterr().out
