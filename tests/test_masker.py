from robot_py.masker import LogMasker


def test_mask_message_screen_title_empty_lpar(monkeypatch):
    """Verify [Screen] is not corrupted when TN5250_HOST is empty."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.delenv("TN5250_HOST", raising=False)

    msg = "[Screen] Main Menu"
    masked = LogMasker.mask_message(msg)
    assert masked == "[Screen] Main Menu"


def test_mask_message_screen_title_with_lpar(monkeypatch):
    """Verify [Screen] title LPAR name is masked when TN5250_HOST is set."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("TN5250_HOST", "pub400")

    msg = "[Screen] pub400 Main Menu"
    masked = LogMasker.mask_message(msg)
    assert masked == "[Screen] *** Main Menu"


def test_mask_hmc_host(monkeypatch):
    """Verify HMC_HOST is masked when present."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("HMC_HOST", "hmc.example.com")

    msg = "Connecting to hmc.example.com via proxy"
    masked = LogMasker.mask_message(msg)
    assert masked == "Connecting to [MASKED_HOST] via proxy"


def test_mask_sensitive_vars_always_active(monkeypatch):
    """Verify secret masking is active regardless of GITHUB_ACTIONS."""
    monkeypatch.setenv("GITHUB_ACTIONS", "false")
    monkeypatch.setenv("TN5250_PASSWORD", "supersecret")

    msg = "User logged in with supersecret"
    masked = LogMasker.mask_message(msg)
    assert masked == "User logged in with ********"
