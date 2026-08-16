from __future__ import annotations

from pathlib import Path

import pytest

from wconfig import Config, ConfigDecodeError


def test_dotenv_supports_quotes_comments_and_blank_values(tmp_path: Path):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        'APP_SERVICE__NAME="quoted value"\n'
        "APP_SERVICE__TOKEN=plain # inline comment\n"
        "APP_SERVICE__EMPTY=",
        encoding="utf-8",
    )

    config = Config(env_prefix="APP").load_dotenv(dotenv_path)

    assert config.as_dict() == {
        "service": {
            "empty": "",
            "name": "quoted value",
            "token": "plain",
        }
    }


def test_load_env_ignores_unprefixed_keys():
    config = Config(env_prefix="APP").load_env(
        {
            "APP_SERVICE__HOST": "api.local",
            "OTHER_SERVICE__HOST": "ignored.local",
        }
    )

    assert config.as_dict() == {
        "service": {
            "host": "api.local",
        }
    }


def test_load_dotenv_supports_export_prefix(tmp_path: Path):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("export APP_SERVICE__HOST=api.local\n", encoding="utf-8")

    config = Config(env_prefix="APP").load_dotenv(dotenv_path)

    assert config.get("service.host") == "api.local"


def test_load_dotenv_last_duplicate_key_wins(tmp_path: Path):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "APP_SERVICE__HOST=first.local\nAPP_SERVICE__HOST=second.local\n",
        encoding="utf-8",
    )

    config = Config(env_prefix="APP").load_dotenv(dotenv_path)

    assert config.get("service.host") == "second.local"


def test_invalid_dotenv_raises_decode_error(tmp_path: Path):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("BROKEN_LINE\n", encoding="utf-8")

    with pytest.raises(ConfigDecodeError, match="Invalid \\.env assignment"):
        Config().load_dotenv(dotenv_path)
