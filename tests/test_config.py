from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pytest

from wconfig import Config, ConfigDecodeError, MissingConfigKeyError, load_config


@dataclass
class DatabaseSettings:
    host: str
    port: int
    enabled: bool


@dataclass
class AppSettings:
    database: DatabaseSettings


def test_precedence_is_defaults_then_file_then_dotenv_then_environment(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("database:\n  host: yaml.local\n  port: 5432\n", encoding="utf-8")

    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("APP_DATABASE__HOST=dotenv.local\nAPP_DATABASE__USER=dotenv-user\n", encoding="utf-8")

    config = (
        Config(env_prefix="APP")
        .load_env({"APP_DATABASE__HOST": "env.local", "APP_DATABASE__PASSWORD": "env-secret"})
        .load_file(config_path)
        .set_defaults({"database": {"host": "default.local", "pool": 5}})
        .load_dotenv(dotenv_path)
    )

    assert config.as_dict() == {
        "database": {
            "host": "env.local",
            "password": "env-secret",
            "pool": 5,
            "port": 5432,
            "user": "dotenv-user",
        }
    }


def test_loaders_support_json_toml_and_yaml(tmp_path):
    json_path = tmp_path / "config.json"
    json_path.write_text('{"service": {"name": "json-app"}}', encoding="utf-8")

    toml_path = tmp_path / "config.toml"
    toml_path.write_text("[service]\nport = 8080\n", encoding="utf-8")

    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text("service:\n  debug: true\n", encoding="utf-8")

    config = Config().load_file(json_path).load_file(toml_path).load_file(yaml_path)

    assert config.as_dict() == {
        "service": {
            "debug": True,
            "name": "json-app",
            "port": 8080,
        }
    }


def test_get_require_and_has_use_nested_keys():
    config = Config().set_defaults({"server": {"host": "localhost", "tls": {"enabled": True}}})

    assert config.get("server.host") == "localhost"
    assert config.get("server.port", 8080) == 8080
    assert config.require("server.tls.enabled") is True
    assert config.has("server.tls.enabled") is True
    assert config.has("server.tls.cert") is False

    with pytest.raises(MissingConfigKeyError):
        config.require("server.port")


def test_dotenv_supports_quotes_comments_and_blank_values(tmp_path):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        '\n'.join(
            [
                'APP_SERVICE__NAME="quoted value"',
                "APP_SERVICE__TOKEN=plain # inline comment",
                "APP_SERVICE__EMPTY=",
            ]
        ),
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


def test_decode_builds_nested_dataclasses():
    config = Config().set_defaults(
        {
            "database": {
                "host": "localhost",
                "port": "5432",
                "enabled": "true",
            }
        }
    )

    settings = config.decode(AppSettings)

    assert settings == AppSettings(database=DatabaseSettings(host="localhost", port=5432, enabled=True))


def test_load_config_convenience_api(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text("[api]\nurl = 'https://file.local'\n", encoding="utf-8")

    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("APP_API__URL=https://dotenv.local\n", encoding="utf-8")

    config = load_config(
        defaults={"api": {"timeout": 5}},
        files=(config_path,),
        dotenv=dotenv_path,
        environ={"APP_API__URL": "https://env.local"},
        env_prefix="APP",
    )

    assert config.as_dict() == {
        "api": {
            "timeout": 5,
            "url": "https://env.local",
        }
    }


def test_invalid_dotenv_raises_decode_error(tmp_path):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("BROKEN_LINE\n", encoding="utf-8")

    with pytest.raises(ConfigDecodeError):
        Config().load_dotenv(dotenv_path)


@dataclass
class ServerSettings:
    env: Literal["dev", "stage", "prod"]
    port: int


def test_decode_supports_literal():
    config = Config().set_defaults({
        "env": "stage",
        "port": 8080
    })
    settings = config.decode(ServerSettings)
    assert settings.env == "stage"
    assert settings.port == 8080


def test_decode_literal_invalid_value_raises_error():
    config = Config().set_defaults({
        "env": "invalid_env",
        "port": 8080
    })
    with pytest.raises(ConfigDecodeError) as exc_info:
        config.decode(ServerSettings)
    assert "Expected one of" in str(exc_info.value)

