import os
import json
import time
import logging
import win32com.client
import yaml
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger("great_sage.discovery")

class AppDiscovery:
    """
    Discovers installed applications on Windows by scanning the Start Menu
    and the Registry.
    """
    def __init__(self, registry_file="app_registry.json", categories_file="app_categories.yaml"):
        self.registry_file = registry_file
        self.categories_file = categories_file

    def _get_category(self, app_name: str) -> str:
        """
        Assigns a category to an app based on keywords in its name.
        """
        try:
            with open(self.categories_file, 'r', encoding='utf-8') as f:
                categories = yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load categories file: {e}")
            return "unknown"

        app_name_lower = app_name.lower()
        for category, keywords in categories.items():
            for kw in keywords:
                if kw.lower() in app_name_lower:
                    return category
        return "unknown"

    def scan(self) -> Dict[str, Any]:
        """
        Scans the system for installed apps and returns a dictionary.
        """
        logger.info("Scanning installed applications...")
        apps = {}

        # 1. Scan Start Menu (.lnk files)
        start_menu_paths = [
            os.path.join(os.environ.get("ProgramData", ""), "Microsoft\\Windows\\Start Menu\\Programs"),
            os.path.join(os.environ.get("AppData", ""), "Microsoft\\Windows\\Start Menu\\Programs"),
        ]

        shell = win32com.client.Dispatch("WScript.Shell")

        for path in start_menu_paths:
            if not os.path.exists(path):
                continue

            for root, _, files in os.walk(path):
                for file in files:
                    if file.endswith(".lnk"):
                        try:
                            lnk_path = os.path.join(root, file)
                            shortcut = shell.CreateShortcut(lnk_path)
                            target = shortcut.TargetPath

                            if target and os.path.exists(target):
                                app_name = os.path.splitext(file)[0]

                                # CORRECTNESS FIX: Filter out uninstallers entirely
                                if "uninstall" in app_name.lower():
                                    continue

                                apps[app_name] = {
                                    "path": target,
                                    "category": self._get_category(app_name)
                                }
                        except Exception as e:
                            logger.debug(f"Failed to resolve shortcut {file}: {e}")

        # 2. Registry scan fallback for apps without shortcuts
        # We avoid adding InstallLocation because it's often just the folder
        import winreg
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        for hkey, subkey in registry_paths:
            try:
                with winreg.OpenKey(hkey, subkey) as key:
                    count = 0
                    while True:
                        try:
                            sub_key_name = winreg.EnumKey(key, count)
                            with winreg.OpenKey(key, sub_key_name) as sub_key:
                                try:
                                    display_name = winreg.QueryValueEx(sub_key, "DisplayName")[0]

                                    if display_name:
                                        if "uninstall" in display_name.lower():
                                            continue

                                        # We only add registry apps if they are NOT already discovered via .lnk
                                        # because .lnk files almost always provide a better full path to the .exe
                                        if display_name not in apps:
                                            # To avoid adding folder paths, we only add it if we can find a likely exe
                                            # For now, we skip adding registry entries that only provide InstallLocation
                                            # since that's exactly what caused the Brave bug.
                                            pass
                                except: pass
                            count += 1
                        except OSError: break
            except: pass

        self.save_registry(apps)
        return apps

    def save_registry(self, apps: Dict[str, Any]):
        try:
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(apps, f, indent=2)
            logger.info(f"App registry saved to {self.registry_file}")
        except Exception as e:
            logger.error(f"Failed to save app registry: {e}")

    def build_if_needed(self):
        if not os.path.exists(self.registry_file):
            logger.info("No app registry found — scanning installed applications...")
            self.scan()
            return True

        mtime = os.path.getmtime(self.registry_file)
        if (time.time() - mtime) > (7 * 24 * 60 * 60):
            logger.info("App registry is stale — rescanning installed applications...")
            self.scan()
            return True

        return False

# Singleton instance
discovery = AppDiscovery()
