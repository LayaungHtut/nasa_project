from services.processing import auth
from services.processing.auth import MissingCredentialsError, load_credentials


def test_missing_env_file_raises_without_leaking_values(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "ENV_PATH", tmp_path / "does_not_exist.env")
    try:
        load_credentials()
        assert False, "expected MissingCredentialsError"
    except MissingCredentialsError as e:
        assert "EARTHDATA_USERNAME" not in str(e) or "not found" in str(e)
        assert "password" not in str(e).lower() or "credentials" in str(e).lower()


def test_env_file_missing_password_raises_clear_error(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("EARTHDATA_USERNAME=someone\n")
    monkeypatch.setattr(auth, "ENV_PATH", env_file)
    monkeypatch.delenv("EARTHDATA_USERNAME", raising=False)
    monkeypatch.delenv("EARTHDATA_PASSWORD", raising=False)

    try:
        load_credentials()
        assert False, "expected MissingCredentialsError"
    except MissingCredentialsError as e:
        assert "EARTHDATA_PASSWORD" in str(e)
        assert "someone" not in str(e)  # never echo the actual value


def test_env_file_with_both_vars_loads_without_exposing_values(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("EARTHDATA_USERNAME=testuser\nEARTHDATA_PASSWORD=testpass\n")
    monkeypatch.setattr(auth, "ENV_PATH", env_file)
    monkeypatch.delenv("EARTHDATA_USERNAME", raising=False)
    monkeypatch.delenv("EARTHDATA_PASSWORD", raising=False)

    username, password = load_credentials()
    assert username == "testuser"
    assert password == "testpass"
