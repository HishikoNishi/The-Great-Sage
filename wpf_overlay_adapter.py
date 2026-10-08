import threading
import logging
import time
from pathlib import Path
import socket
import subprocess
import psutil
import win32job
import win32process
import win32api
import base64
import mimetypes

logger = logging.getLogger("great_sage.wpf_adapter")

class WpfOverlayAdapter:
    """
    Adapter that manages the external WPF Host process.
    Implements the same interface as the pywebview-based OverlayManager
    to ensure zero changes are needed in the main application logic.
    """
    def __init__(self):
        self.process = None
        self.is_ready = False
        self._ready_event = threading.Event()
        self._shutdown_event = threading.Event()
        self.host_address = ("127.0.0.1", 9999)
        self.event_address = ("127.0.0.1", 9998)
        self._job_handle = None

        # Event listener state
        self._stop_event_listener = threading.Event()
        self._event_listener_thread = None

        # Mapping of audio_id -> threading.Event for synchronization
        self._audio_events = {}
        self._events_lock = threading.Lock()

        # Mock window object to satisfy existing code: overlay.window.show()/hide()
        class MockWindow:
            def show(self):
                logger.info("WPF Window: show() called")
                pass
            def hide(self):
                logger.info("WPF Window: hide() called")
                pass

        self.window = MockWindow()

    def set_visibility(self, visible: bool):
        """Controls the visibility of the Great Sage Core visual element."""
        val = "true" if visible else "false"
        self._send_js(f"window.setVisibility({val})", f"setVisibility({visible})")

    def show(self):
        """Explicitly show the Core."""
        self.set_visibility(True)

    def hide(self):
        """Explicit lauch of hide animation."""
        self.set_visibility(False)

    def start(self):
        """Launches the external WPF Host process and the reverse event listener."""
        logger.info("Starting WPF Host process...")

        self._cleanup_existing_hosts()

        exe_path = Path("wpf_poc_host.exe").resolve()
        if not exe_path.exists():
            logger.error(f"WPF Host executable not found at {exe_path}")
            raise FileNotFoundError(f"WPF Host missing: {exe_path}")

        try:
            self._job_handle = win32job.CreateJobObject(None, "")
            info = win32job.QueryInformationJobObject(self._job_handle, win32job.JobObjectExtendedLimitInformation)
            info['BasicLimitInformation']['LimitFlags'] |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            win32job.SetInformationJobObject(self._job_handle, win32job.JobObjectExtendedLimitInformation, info)

            self.process = subprocess.Popen(
                [str(exe_path)],
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )

            win32job.AssignProcessToJobObject(self._job_handle, self.process._handle)

            logger.info(f"WPF Host launched (PID: {self.process.pid}) and tied to Job Object.")

            self._stop_event_listener.clear()
            self._event_listener_thread = threading.Thread(target=self._run_event_listener, daemon=True)
            self._event_listener_thread.start()

            threading.Thread(target=self._wait_for_ready, daemon=True).start()

        except Exception as e:
            logger.exception(f"Failed to launch WPF Host: {e}")

    def _run_event_listener(self):
        """Listens for events from the WPF Host on port 9998."""
        logger.info("[AUDIO_TRACE] Python reverse listener socket creating...")
        logger.info(f"Starting WPF reverse event listener on {self.event_address}...")

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                logger.info("[AUDIO_TRACE] Python reverse listener socket created")
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(self.event_address)
                logger.info(f"[AUDIO_TRACE] Python reverse listener bound {self.event_address[0]}:{self.event_address[1]}")
                s.listen(5)
                logger.info("[AUDIO_TRACE] Python reverse listener listening")
                s.settimeout(1.0)

                logger.info("[AUDIO_TRACE] Python listener thread started - entering loop")
                while not self._stop_event_listener.is_set():
                    try:
                        logger.info("[AUDIO_TRACE] Python listener waiting in accept()")
                        client, addr = s.accept()
                        logger.info(f"[AUDIO_TRACE] Python listener accepted connection from {addr}")
                        with client:
                            raw_data = client.recv(1024)
                            if not raw_data:
                                logger.info("[AUDIO_TRACE] Python listener received empty packet")
                                continue
                            data = raw_data.decode('utf-8').strip()
                            logger.info(f"[AUDIO_TRACE] Python listener raw message={data}")
                            # Expected format: "EVENT_TYPE:AUDIO_ID"
                            if ":" in data:
                                event_type, audio_id = data.split(":", 1)
                                logger.info(f"[AUDIO_TRACE] Python parsed event_type={event_type} audio_id={audio_id}")
                                if event_type in ("AUDIO_ENDED", "AUDIO_ERROR"):
                                    logger.info(f"Received {event_type} for audio {audio_id}")
                                    with self._events_lock:
                                        if audio_id in self._audio_events:
                                            logger.info(f"[AUDIO_TRACE] Python Event.set() id={audio_id}")
                                            self._audio_events[audio_id].set()
                                        else:
                                            logger.info(f"[AUDIO_TRACE] Python AUDIO_ENDED ID NOT FOUND: {audio_id}")
                                            logger.info(f"[AUDIO_TRACE] Python known audio IDs: {list(self._audio_events.keys())}")
                    except socket.timeout:
                        continue
                    except Exception as e:
                        if not self._stop_event_listener.is_set():
                            logger.exception(f"[AUDIO_TRACE] Python listener loop exception: {e}")
        except Exception as e:
            logger.exception(f"[AUDIO_TRACE] Critical failure in event listener thread: {e}")
        finally:
            logger.info("[AUDIO_TRACE] Python listener thread EXIT")

    def register_audio_event(self, audio_id: str) -> threading.Event:
        """Creates and returns a threading.Event for a specific audio ID."""
        with self._events_lock:
            logger.info(f"[AUDIO_TRACE] register id={audio_id}")
            event = threading.Event()
            self._audio_events[audio_id] = event
            return event

    def clear_audio_event(self, audio_id: str):
        """Removes the event from the tracking map."""
        with self._events_lock:
            logger.info(f"[AUDIO_TRACE] clear id={audio_id}")
            self._audio_events.pop(audio_id, None)

    def _cleanup_existing_hosts(self):
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] == 'wpf_poc_host.exe':
                    logger.info(f"Cleaning up orphan WPF Host (PID: {proc.info['pid']})")
                    proc.terminate()
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error during WPF Host cleanup: {e}")

    def _wait_for_ready(self):
        timeout = 10
        start = time.time()
        while time.time() - start < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    s.connect(self.host_address)
                    logger.info("WPF Host is ready and listening.")
                    self.is_ready = True
                    self._ready_event.set()
                    return
            except socket.error:
                time.sleep(0.5)

        logger.warning("WPF Host timed out while waiting for readiness.")

    def run(self, on_ready=None):
        self._ready_event.wait(timeout=15)
        if on_ready:
            on_ready()

        # Keep main thread alive until shutdown is requested
        self._shutdown_event.wait()
        logger.info("[SHUTDOWN_TRACE] _shutdown_event.wait() returned")

    def _send_js(self, script: str, error_context: str | None = None):
        if not self.is_ready:
            logger.warning(f"WPF Host not ready. Dropping command: {script}")
            return

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                s.connect(self.host_address)
                s.sendall((script + "\n").encode('utf-8'))
        except Exception as e:
            logger.error(f"Communication error sending JS ({error_context}): {e}")

    def set_mode(self, mode: str):
        safe_mode = mode.replace("'", "\'")
        self._send_js(f"window.setMode('{safe_mode}')", f"set_mode('{mode}')")

    def set_caption(self, text: str):
        safe_text = text.replace("'", "\'").replace("\n", "\n").replace("\r", "")
        self._send_js(f"window.setCaption('{safe_text}')", "set_caption")

    def play_voice_line(self, file_url: str, audio_id: str = None):
        """
        Reads an audio file, encodes it to Base64, and sends it as a Data URI.
        Now supports an audio_id for synchronized event tracking.
        """
        try:
            path = Path(file_url).resolve()
            if not path.exists():
                logger.error(f"Voice file not found for playback: {path}")
                return

            mime_type, _ = mimetypes.guess_type(str(path))
            if not mime_type:
                mime_type = "audio/mpeg"

            with open(path, "rb") as audio_file:
                binary_data = audio_file.read()
                base64_audio = base64.b64encode(binary_data).decode('utf-8')
                data_uri = f"data:{mime_type};base64,{base64_audio}"

            # Send the Data URI and the audio_id to JS
            self._send_js(f"window.playVoiceLine('{data_uri}', '{audio_id}')", "play_voice_line")

        except Exception as e:
            logger.exception(f"Failed to encode audio for playback: {e}")

    def play_ui_sfx(self, sfx_key: str):
        safe_key = sfx_key.replace("'", "\'")
        self._send_js(f"window.playUiSfx && window.playUiSfx('{safe_key}')", "play_ui_sfx")

    def trigger_success(self):
        self._send_js("window.triggerSuccess && window.triggerSuccess()", "trigger_success")

    def trigger_failure(self):
        self._send_js("window.triggerFailure && window.triggerFailure()", "trigger_failure")

    def stop(self):
        logger.info("[SHUTDOWN_TRACE] WpfOverlayAdapter.stop() called")
        self._shutdown_event.set()
        self._stop_event_listener.set()
        if self._event_listener_thread:
            self._event_listener_thread.join(timeout=1.0)

        if self.process:
            try:
                self.process.terminate()
                if self._job_handle:
                    win32api.CloseHandle(self._job_handle)
                    self._job_handle = None
            except Exception as e:
                logger.error(f"Error while stopping WPF Host: {e}")
