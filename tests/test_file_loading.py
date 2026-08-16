from __future__ import annotations

from pathlib import Path

import pytest

from wconfig import (
    Config,
    ConfigDecodeError,
    ConfigFileNotFoundError,
    UnsupportedConfigFormatError,
)


def test_loaders_support_json_toml_and_yaml(tmp_path: Path):
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


def test_load_file_rejects_non_mapping_top_level_json(tmp_path: Path):
    config_path = tmp_path / "config.json"
    config_path.write_text('["not", "a", "mapping"]', encoding="utf-8")

    with pytest.raises(ConfigDecodeError, match="must be a mapping"):
        Config().load_file(config_path)


def test_load_file_returns_empty_mapping_for_empty_yaml(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("", encoding="utf-8")

    assert Config().load_file(config_path).as_dict() == {}


def test_load_file_raises_file_not_found_for_missing_path(tmp_path: Path):
    missing_path = tmp_path / "missing.yaml"

    with pytest.raises(ConfigFileNotFoundError):
        Config().load_file(missing_path)


def test_load_file_rejects_unsupported_extension(tmp_path: Path):
    config_path = tmp_path / "config.ini"
    config_path.write_text("[service]\nport=8080\n", encoding="utf-8")

    with pytest.raises(UnsupportedConfigFormatError, match="Unsupported config format"):
        Config().load_file(config_path)
