import pytest
from robot_py.engine import validate_environment, SUPPORTED_24x80, RobotEngine


def test_validate_environment_direct_success(monkeypatch):
    """Test successful validation for direct IP connection."""
    monkeypatch.setenv("TN5250_HOST", "test_host")
    monkeypatch.setenv("TN5250_USER", "test_user")
    monkeypatch.setenv("TN5250_PASSWORD", "test_password")
    # Should not raise
    validate_environment()


@pytest.mark.parametrize(
    "missing_var", ["TN5250_HOST", "TN5250_USER", "TN5250_PASSWORD"]
)
def test_validate_environment_direct_missing_vars(monkeypatch, missing_var):
    """Test validation failure for various missing variables in direct IP mode."""
    monkeypatch.setenv("TN5250_HOST", "test_host")
    monkeypatch.setenv("TN5250_USER", "test_user")
    monkeypatch.setenv("TN5250_PASSWORD", "test_password")
    monkeypatch.delenv(missing_var, raising=False)

    with pytest.raises(
        ValueError,
        match=rf"Missing required environment variables for Direct IP connection: .*{missing_var}.*",
    ):
        validate_environment()


def test_validate_environment_direct_multiple_missing(monkeypatch):
    """Test validation failure when multiple variables are missing."""
    monkeypatch.delenv("TN5250_HOST", raising=False)
    monkeypatch.delenv("TN5250_USER", raising=False)
    monkeypatch.delenv("TN5250_PASSWORD", raising=False)

    with pytest.raises(
        ValueError,
        match=r"Missing required environment variables for Direct IP connection: TN5250_USER, TN5250_PASSWORD, TN5250_HOST",
    ):
        validate_environment()


def test_validate_environment_empty_string(monkeypatch):
    """Test validation failure when a variable is an empty string."""
    monkeypatch.setenv("TN5250_HOST", "")
    monkeypatch.setenv("TN5250_USER", "user")
    monkeypatch.setenv("TN5250_PASSWORD", "pwd")

    with pytest.raises(
        ValueError,
        match=r"Missing required environment variables for Direct IP connection: TN5250_HOST",
    ):
        validate_environment()


def test_validate_environment_hmc_success(monkeypatch):
    """Test successful validation for HMC proxy connection."""
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


@pytest.mark.parametrize(
    "missing_var",
    [
        "HMC_USER",
        "HMC_PWD",
        "HMC_SYSNAME",
        "HMC_LPARNAME",
        "HMC_SESSION_KEY",
        "TN5250_USER",
        "TN5250_PASSWORD",
    ],
)
def test_validate_environment_hmc_missing_vars(monkeypatch, missing_var):
    """Test validation failure for various missing variables in HMC proxy mode."""
    monkeypatch.setenv("HMC_HOST", "hmc_host")
    monkeypatch.setenv("HMC_USER", "hmc_user")
    monkeypatch.setenv("HMC_PWD", "hmc_pwd")
    monkeypatch.setenv("HMC_SYSNAME", "sysname")
    monkeypatch.setenv("HMC_LPARNAME", "lparname")
    monkeypatch.setenv("HMC_SESSION_KEY", "session_key")
    monkeypatch.setenv("TN5250_USER", "tn_user")
    monkeypatch.setenv("TN5250_PASSWORD", "tn_password")
    monkeypatch.delenv(missing_var, raising=False)

    with pytest.raises(
        ValueError,
        match=rf"Missing required environment variables for HMC Proxy connection: .*{missing_var}.*",
    ):
        validate_environment()


def test_validate_environment_invalid_device_type(monkeypatch):
    """Test validation failure for an unsupported device type."""
    monkeypatch.setenv("TN5250_HOST", "test_host")
    monkeypatch.setenv("TN5250_USER", "test_user")
    monkeypatch.setenv("TN5250_PASSWORD", "test_password")
    monkeypatch.setenv("TN5250_DEVICE_TYPE", "INVALID_DEVICE")

    with pytest.raises(
        ValueError, match=r"Unsupported TN5250_DEVICE_TYPE: INVALID_DEVICE"
    ):
        validate_environment()


def test_validate_environment_valid_device_type(monkeypatch):
    """Test successful validation with a valid device type."""
    monkeypatch.setenv("TN5250_HOST", "test_host")
    monkeypatch.setenv("TN5250_USER", "test_user")
    monkeypatch.setenv("TN5250_PASSWORD", "test_password")
    monkeypatch.setenv("TN5250_DEVICE_TYPE", SUPPORTED_24x80[0])
    # Should not raise
    validate_environment()


def test_robot_engine_init_validation_failure(monkeypatch, tmp_path):
    """Integration test: Verify RobotEngine fails fast on init if env is invalid."""
    monkeypatch.setenv("TN5250_USER", "user")
    monkeypatch.setenv("TN5250_PASSWORD", "pwd")
    monkeypatch.delenv("TN5250_HOST", raising=False)
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("name: Test\nsteps: []")

    with pytest.raises(
        ValueError,
        match="Missing required environment variables for Direct IP connection: TN5250_HOST",
    ):
        RobotEngine(str(yaml_file))
