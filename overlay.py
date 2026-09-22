import webview
import os
import logging
from pathlib import Path
from config import OVERLAY_FILE

try:
    from webview.errors import JavascriptException
except ImportError:
    JavascriptException = Exception  # type: ignore[misc, assignment]

logger = logging.getLogger("great_sage.overlay")


def _format_javascript_exception(exc: Exception) -> str:
    """Extract name/message/stack from pywebview's JavascriptException payload."""
    payload = exc.args[0] if exc.args else None
    if isinstance(payload, dict):
        name = payload.get("name", "Error")
        message = payload.get("message", "")
        stack = payload.get("stack", "")
        return f"{name}: {message} | stack: {stack} | full: {payload}"
    return repr(exc)


class OverlayManager:
    """Manages the pywebview window for the Great Sage visual core."""

    def __init__(self):
        self.window = None
        self._page_ready = False
        self._pending_ready_callback = None
        self._js_queue: list[tuple[str, str | None]] = []

    def start(self):
        """Creates the borderless, transparent overlay window (loop not started yet)."""
        overlay_path = Path(OVERLAY_FILE).resolve()
        if not overlay_path.is_file():
            logger.error(f"Overlay file not found at {overlay_path}")
            raise FileNotFoundError(f"Missing overlay asset: {overlay_path}")

        self._page_ready = False
        self._js_queue.clear()

        self.window = webview.create_window(
            "Great Sage Core",
            url=overlay_path.as_uri(),
            frameless=True,
            transparent=True,
            on_top=True,
            width=800,
            height=600,
            resizable=False,
        )
        self.window.events.loaded += self._on_window_loaded

    def _on_window_loaded(self):
        logger.info("Overlay page loaded.")
        self._page_ready = True

        for script, error_context in self._js_queue:
            self._evaluate_js(script, queue=False, error_context=error_context)
        self._js_queue.clear()

        cb = self._pending_ready_callback
        if cb:
            self._pending_ready_callback = None
            try:
                cb()
            except Exception:
                logger.exception("Overlay ready callback failed")

    def run(self, on_ready=None):
        """Starts the webview event loop (blocks on main thread)."""
        self._pending_ready_callback = on_ready
        webview.start(debug=True)

    def _evaluate_js(
        self,
        script: str,
        *,
        queue: bool = True,
        error_context: str | None = None,
    ):
        if not self.window:
            return
        if not self._page_ready:
            if queue:
                self._js_queue.append((script, error_context))
            return
        try:
            self.window.evaluate_js(script)
        except JavascriptException as exc:
            details = _format_javascript_exception(exc)
            if error_context:
                logger.error(
                    "JS error in %s: %s | evaluate_js script=%r",
                    error_context,
                    details,
                    script,
                )
            else:
                logger.warning("Overlay JS evaluation failed: %s", details)

    def set_mode(self, mode: str):
        """Update the visual mode via JS."""
        safe_mode = mode.replace("'", "\\'")
        self._evaluate_js(
            f"window.setMode('{safe_mode}')",
            error_context=f"set_mode('{mode}')",
        )

    def set_caption(self, text: str):
        """Update the caption text via JS."""
        safe_text = text.replace("'", "\\'").replace("\n", "\\n").replace("\r", "")
        preview = text if len(text) <= 80 else text[:77] + "..."
        self._evaluate_js(
            f"window.setCaption('{safe_text}')",
            error_context=f"set_caption({preview!r})",
        )

    def play_voice_line(self, file_url: str):
        """Play a voice line and drive the visualizer via JS."""
        url = Path(file_url).resolve().as_uri()
        safe_url = url.replace("'", "\\'")
        self._evaluate_js(
            f"window.playVoiceLine('{safe_url}')",
            error_context=f"play_voice_line({url!r})",
        )

    def play_ui_sfx(self, sfx_key: str):
        """Fire-and-forget UI sound effect in the overlay (separate from voice audio)."""
        safe_key = sfx_key.replace("'", "\\'")
        self._evaluate_js(f"window.playUiSfx && window.playUiSfx('{safe_key}')")

    def trigger_success(self):
        """One-shot success animation in the overlay."""
        self._evaluate_js("window.triggerSuccess && window.triggerSuccess()")

    def trigger_failure(self):
        """One-shot failure animation in the overlay."""
        self._evaluate_js("window.triggerFailure && window.triggerFailure()")


# Singleton instance
overlay = OverlayManager()
