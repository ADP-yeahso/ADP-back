from app.core.config import Settings


def test_settings_load_env_from_backend_directory() -> None:
    env_file = Settings.model_config["env_file"]

    assert env_file.name == ".env"
    assert env_file.parent.name == "backend"
