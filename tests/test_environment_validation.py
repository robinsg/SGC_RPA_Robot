import pytest
from robot_py.engine import validate_environment, SUPPORTED_24x80


def test_validate_environment_direct_success(monkeypatch):
    monkeypatch.setenv("TN5250_HOST", "test_host")
    monkeypatch.setenv("TN5250_USER", "test_user")
    monkeypatch.setenv("TN5250_PASSWORD", "test_password")
    # Should not raise
    validate_environment()


def test_validate_environment_direct_missing_var(monkeypatch):
    monkeypatch.setenv("TN5250_HOST", "test_host")
    monkeypatch.setenv("TN5250_USER", "test_user")
    monkeypatch.delenv("TN5250_PASSWORD", raising=False)

    with pytest.raises(ValueError) as excinfo:
        validate_environment()
    assert "Missing required environment variables: TN5250_PASSWORD" in str(
        excinfo.value
    )


def test_validate_environment_hmc_success(monkeypatch):
    monkeypatch.setenv("HMC_HOST", "hmc_host")
    monkeypatch.setenv("HMC_USER", "hmc_user")
    monkeypatch.setenv("HMC_PWD", "hmc_pwd")
    monkeypatch.setenv("HMC_SYSNAME", "sysname")
    monkeypatch.setenv("HMC_LPARNAME", "lparname")
    monkeypatch.setenv("HMC_SESSION_KEY", "session_key")
    monkeypatch.setenv("TN5250_USER", "tn_user")
    monkeypatch.setenv("TN5250_PASSWORD", "tn_password")
    # Should not raise
    validate_environment()


def test_validate_environment_hmc_missing_var(monkeypatch):
    monkeypatch.setenv("HMC_HOST", "hmc_host")
    monkeypatch.setenv("HMC_USER", "hmc_user")
    # HMC_PWD missing
    monkeypatch.setenv("HMC_SYSNAME", "sysname")
    monkeypatch.setenv("HMC_LPARNAME", "lparname")
    monkeypatch.setenv("HMC_SESSION_KEY", "session_key")
    monkeypatch.setenv("TN5250_USER", "tn_user")
    monkeypatch.setenv("TN5250_PASSWORD", "tn_password")

    with pytest.raises(ValueError) as excinfo:
        validate_environment()
    assert "HMC_PWD" in str(excinfo.value)


def test_validate_environment_invalid_device_type(monkeypatch):
    monkeypatch.setenv("TN5250_HOST", "test_host")
    monkeypatch.setenv("TN5250_USER", "test_user")
    monkeypatch.setenv("TN5250_PASSWORD", "test_password")
    monkeypatch.setenv("TN5250_DEVICE_TYPE", "INVALID_DEVICE")

    with pytest.raises(ValueError) as excinfo:
        validate_environment()
    assert "Unsupported TN5250_DEVICE_TYPE: INVALID_DEVICE" in str(excinfo.value)


def test_validate_environment_valid_device_type(monkeypatch):
    monkeypatch.setenv("TN5250_HOST", "test_host")
    monkeypatch.setenv("TN5250_USER", "test_user")
    monkeypatch.setenv("TN5250_PASSWORD", "test_password")
    monkeypatch.setenv("TN5250_DEVICE_TYPE", SUPPORTED_24x80[0])
    # Should not raise
    validate_environment()
