from __future__ import annotations

from pathlib import Path

from wconfig import Config


def test_precedence_is_defaults_then_file_then_dotenv_then_environment(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "database:\n  host: yaml.local\n  port: 5432\n", encoding="utf-8"
    )

    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "APP_DATABASE__HOST=dotenv.local\nAPP_DATABASE__USER=dotenv-user\n",
        encoding="utf-8",
    )

    config = (
        Config(env_prefix="APP")
        .load_env(
            {"APP_DATABASE__HOST": "env.local", "APP_DATABASE__PASSWORD": "env-secret"}
        )
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


def test_load_files_merges_same_priority_sources_in_call_order(tmp_path: Path):
    first_path = tmp_path / "base.yaml"
    first_path.write_text(
        "service:\n  host: base.local\n  port: 8080\n", encoding="utf-8"
    )

    second_path = tmp_path / "override.yaml"
    second_path.write_text("service:\n  host: override.local\n", encoding="utf-8")

    config = Config().load_files(first_path, second_path)

    assert config.as_dict() == {
        "service": {
            "host": "override.local",
            "port": 8080,
        }
    }


def test_sources_reports_source_order_and_metadata(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("service:\n  port: 8080\n", encoding="utf-8")

    config = (
        Config(env_prefix="APP")
        .set_defaults({"service": {"host": "localhost"}}, name="code-defaults")
        .load_file(config_path, name="main-config")
        .load_env({"APP_SERVICE__HOST": "env.local"})
    )

    assert config.sources() == (
        config.sources()[0].__class__(
            name="code-defaults", kind="defaults", priority=10, order=0, origin=None
        ),
        config.sources()[1].__class__(
            name="main-config",
            kind="file",
            priority=20,
            order=1,
            origin=str(config_path),
        ),
        config.sources()[2].__class__(
            name="environment", kind="env", priority=40, order=2, origin=None
        ),
    )
