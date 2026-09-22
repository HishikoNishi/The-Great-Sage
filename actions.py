import os
import subprocess
import pyautogui
from typing import Any, Dict
import logging

logger = logging.getLogger("great_sage.actions")

class ActionExecutor:
    """Executes whitelisted keyboard and mouse actions."""

    def __init__(self):
        # Pre-defined app paths or shortcuts could go here
        self.app_shortcuts = {
            "explorer": "explorer.exe",
            "vscode": "code",
            "browser": "brave",
            "music": "spotify",  # Example
        }

    def execute(self, action_name: str, params: Dict[str, Any]) -> bool:
        """Dispatch to the correct whitelisted action."""
        method_name = f"_{action_name}"
        if hasattr(self, method_name):
            try:
                method = getattr(self, method_name)
                return method(**params)
            except Exception as e:
                logger.error(f"Error executing action {action_name}: {e}")
                return False
        else:
            logger.warning(f"Action {action_name} is not whitelisted.")
            return False

    def _open_app(self, app_name: str = None, url: str = None) -> bool:
        """Open an application by name or a URL in the default browser."""
        if url:
            try:
                os.startfile(url)
                return True
            except Exception as e:
                logger.error(f"Failed to open URL {url}: {e}")
                return False

        if not app_name:
            logger.warning("_open_app called without app_name or url")
            return False

        app_path = self.app_shortcuts.get(app_name, app_name)
        try:
            # Use startfile on Windows to handle shortcuts/exe
            os.startfile(app_path)
            return True
        except Exception as e:
            logger.error(f"Failed to open app {app_name}: {e}")
            return False

    def _type_text(self, text: str) -> bool:
        """Type text using pyautogui."""
        pyautogui.write(text)
        return True

    def _press_keys(self, keys: list) -> bool:
        """Press a combination of keys."""
        pyautogui.hotkey(*keys)
        return True

    def _move_mouse(self, x: int, y: int) -> bool:
        """Move mouse to coordinates."""
        pyautogui.moveTo(x, y)
        return True

    def _click(self, x: int, y: int, button: str = "left") -> bool:
        """Click at coordinates."""
        pyautogui.click(x, y, button=button)
        return True

    def _scroll(self, amount: int) -> bool:
        """Scroll the mouse wheel."""
        pyautogui.scroll(amount)
        return True

    def _system_cmd(self, cmd: str) -> bool:
        """Execute a whitelisted system shell command."""
        try:
            subprocess.run(cmd, shell=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"System command failed: {e}")
            return False

# Singleton instance
executor = ActionExecutor()
