"""Main entry point — loads credentials from ~/.zshrc and DB, then launches the app."""

import os
import subprocess

from app.ui.app_window import AppWindow


def _load_env_from_zshrc() -> None:
    """Load Atlassian env vars from ~/.zshrc if not already set."""
    if os.environ.get("ATLASSIAN_EMAIL") and os.environ.get("ATLASSIAN_API_TOKEN"):
        return
    try:
        result = subprocess.run(
            ["zsh", "-c", "source ~/.zshrc && env"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        for line in result.stdout.splitlines():
            if line.startswith(("ATLASSIAN_EMAIL=", "ATLASSIAN_API_TOKEN=")):
                key, _, val = line.partition("=")
                os.environ[key] = val
    except Exception:
        pass


def _load_env_from_db() -> None:
    """Load tokens and settings stored in the DB that are not yet in os.environ."""
    try:
        from app.db import get_all_tokens, get_setting, init_db
        init_db()
        # Tokens (ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN)
        for key, val in get_all_tokens().items():
            if val and not os.environ.get(key):
                os.environ[key] = val
        # Board URL
        url = get_setting("JIRA_BOARD_URL", "")
        if url and not os.environ.get("JIRA_BOARD_URL"):
            os.environ["JIRA_BOARD_URL"] = url
    except Exception:
        pass


if __name__ == "__main__":
    _load_env_from_zshrc()
    _load_env_from_db()
    app = AppWindow()
    app.mainloop()
