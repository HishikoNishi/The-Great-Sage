import os
import subprocess
import pyautogui
from typing import Any, Dict, Union
import logging

logger = logging.getLogger("great_sage.actions")

class ActionExecutor:
    """Executes whitelisted keyboard and mouse actions."""

    def __init__(self):
        # Pre-defined app paths or shortcuts are now in app_registry.json and handled by AppResolver
        from resolver import resolver, ClarificationRequired
        self.resolver = resolver
        self.ClarificationRequired = ClarificationRequired


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

        # Use the resolver to get the resolved app NAME (the key in the registry)
        resolution = self.resolver.resolve(app_name)

        if isinstance(resolution, str):
            # resolution is the KEY (e.g. "Riot Client")
            # Look up the actual executable path in the registry
            app_data = self.resolver.registry.get(resolution)
            if app_data and isinstance(app_data, dict) and "path" in app_data:
                app_path = app_data["path"]
                try:
                    os.startfile(app_path)
                    return True
                except Exception as e:
                    logger.error(f"Failed to start app {resolution} at path {app_path}: {e}")
                    return False
            else:
                logger.error(f"Resolved name {resolution} not found in registry or missing path.")
                return False
        elif isinstance(resolution, self.ClarificationRequired):
            # Ambiguity detected: return False to trigger clarification flow in main.py
            logger.info(f"Clarification required for app {app_name}")
            return "CLARIFICATION_REQUIRED"
        else:
            # Not found (None)
            logger.warning(f"App {app_name} could not be resolved")
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
