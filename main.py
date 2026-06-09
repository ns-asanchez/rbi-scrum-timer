"""Main entry point — loads Jira credentials from ~/.zshrc and launches the app."""

import os
import subprocess

from app.ui.app_window import AppWindow


def _load_env_from_zshrc() -> None:
    """Load ATLASSIAN_EMAIL and ATLASSIAN_API_TOKEN from ~/.zshrc if not already set."""
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


if __name__ == "__main__":
    _load_env_from_zshrc()
    app = AppWindow()
    app.mainloop()
