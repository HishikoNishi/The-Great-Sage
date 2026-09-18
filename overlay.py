import webview
import os
import logging
from config import OVERLAY_FILE

logger = logging.getLogger("great_sage.overlay")

class OverlayManager:
    """Manages the pywebview window for the Great Sage visual core."""

    def __init__(self):
        self.window = None

    def start(self):
        """Launches the borderless, transparent overlay window."""
        overlay_path = str(OVERLAY_FILE)
        if not os.path.exists(overlay_path):
            logger.error(f"Overlay file not found at {overlay_path}")
            raise FileNotFoundError(f"Missing overlay asset: {overlay_path}")

        # Create window with HUD-like settings
        # Note: transparency and frameless depend on the OS and pywebview version
        self.window = webview.create_window(
            "Great Sage Core",
            url=f"file://{overlay_path}",
            frameless=True,
            transparent=True,
            on_top=True,
            width=800,
            height=600,
            resizable=False
        )

        # Start webview in a background thread or the main loop
        # we use start() but usually it blocks, so main.py will call it in a thread
        # or use the pywebview loop.

    def run(self):
        """Starts the webview event loop."""
        webview.start()

    def set_mode(self, mode: str):
        """Update the visual mode via JS."""
        if self.window:
            self.window.evaluate_js(f"window.setMode('{mode}')")

    def set_caption(self, text: str):
        """Update the caption text via JS."""
        if self.window:
            # Escape single quotes for JS
            safe_text = text.replace("'", "\\'")
            self.window.evaluate_js(f"window.setCaption('{safe_text}')")

    def play_voice_line(self, file_url: str):
        """Play a voice line and drive the visualizer via JS."""
        if self.window:
            # Convert local path to file:// URL
            url = f"file://{file_url}"
            # This returns a promise in JS; we can't easily await it in evaluate_js
            # but the JS function handles the playback and reactivity.
            self.window.evaluate_js(f"window.playVoiceLine('{url}')")

# Singleton instance
overlay = OverlayManager()
