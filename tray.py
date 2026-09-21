import pystray
from PIL import Image, ImageDraw
import threading
import logging
from typing import Callable

logger = logging.getLogger("great_sage.tray")

class TrayManager:
    """Manages the system tray icon and control menu."""

    def __init__(
        self,
        on_listen: Callable,
        on_pause: Callable,
        on_quit: Callable,
        on_menu_click: Callable | None = None,
    ):
        self.on_listen = on_listen
        self.on_pause = on_pause
        self.on_quit = on_quit
        self.on_menu_click = on_menu_click
        self.icon = None
        self.running = False

    def create_image(self):
        """Create a simple icon image (white circle on black bg)."""
        width, height = 64, 64
        image = Image.new('RGB', (width, height), color=(0, 0, 0))
        dc = ImageDraw.Draw(image)
        dc.ellipse([10, 10, 54, 54], fill=(255, 255, 255))
        return image

    def start(self):
        """Launches the tray icon in a separate thread."""
        menu = pystray.Menu(
            pystray.MenuItem("Listen now", self._on_listen_clicked),
            pystray.MenuItem("Pause", self._on_pause_clicked),
            pystray.MenuItem("Quit", self._on_quit_clicked)
        )

        self.icon = pystray.Icon("Great Sage", self.create_image(), "Great Sage", menu)

        # Run in a thread so it doesn't block main.py
        self.thread = threading.Thread(target=self.icon.run)
        self.thread.daemon = True
        self.thread.start()
        self.running = True
        logger.info("System tray icon started.")

    def _menu_action(self, action: Callable):
        if self.on_menu_click:
            self.on_menu_click()
        action()

    def _on_listen_clicked(self, icon, item):
        self._menu_action(self.on_listen)

    def _on_pause_clicked(self, icon, item):
        self._menu_action(self.on_pause)

    def _on_quit_clicked(self, icon, item):
        self._menu_action(self.on_quit)

    def stop(self):
        """Stop the tray icon."""
        if self.icon:
            self.icon.stop()
        self.running = False
