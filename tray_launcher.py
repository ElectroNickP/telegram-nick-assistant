#!/usr/bin/env python3
"""
System tray for Telegram Nick Assistant.
- Icon shows state: running (green) / stopped (gray).
- Menu: Start, Stop, Restart, Quit (tray only).
- Uses systemd --user for start/stop; service auto-starts at login and restarts on failure.
Run: python tray_launcher.py
Or add to autostart via install-tray-and-service.sh.
"""

import subprocess
import sys
import threading
import time
from pathlib import Path

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    print("Install tray deps: pip install pystray Pillow")
    sys.exit(1)

SERVICE_NAME = "telegram-nick-assistant"
PROJECT_ROOT = Path(__file__).resolve().parent


def _systemctl_user(*args, timeout: int = 15) -> bool:
    """Run systemctl --user. Returns True if exit code 0."""
    try:
        r = subprocess.run(
            ["systemctl", "--user"] + list(args),
            capture_output=True,
            timeout=timeout,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def is_service_active() -> bool:
    """True if the user service is active (running)."""
    try:
        r = subprocess.run(
            ["systemctl", "--user", "is-active", SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return r.returncode == 0 and (r.stdout or "").strip() == "active"
    except Exception:
        return False


def start_service() -> bool:
    """Start the service. Returns True on success."""
    if is_service_active():
        return True
    if _systemctl_user("start", SERVICE_NAME):
        time.sleep(1.0)
        return is_service_active()
    return False


def stop_service() -> bool:
    """Stop the service. Returns True when stopped."""
    if not is_service_active():
        return True
    _systemctl_user("stop", SERVICE_NAME, timeout=20)
    time.sleep(1.5)
    return not is_service_active()


def restart_service() -> bool:
    """Restart the service."""
    _systemctl_user("restart", SERVICE_NAME, timeout=25)
    time.sleep(2.0)
    return is_service_active()


def create_icon_image(size: int = 64, running: bool = True) -> Image.Image:
    """Create tray icon: green if running, gray if stopped."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    margin = 6
    if running:
        fill = (76, 175, 80)  # green
        outline = (56, 142, 60)
    else:
        fill = (158, 158, 158)  # gray
        outline = (97, 97, 97)
    d.ellipse([margin, margin, size - margin, size - margin], fill=fill, outline=outline, width=2)
    return img


def run_tray():
    """Run the system tray icon and menu."""
    icon_running = create_icon_image(64, running=True)
    icon_stopped = create_icon_image(64, running=False)

    current_icon = [icon_stopped]
    if is_service_active():
        current_icon[0] = icon_running

    def update_icon_state():
        """Refresh icon and title by current service state (call from timer thread)."""
        try:
            active = is_service_active()
            current_icon[0] = icon_running if active else icon_stopped
            if hasattr(icon, "_icon"):
                icon._icon = current_icon[0]
            if hasattr(icon, "update_icon"):
                icon.update_icon(current_icon[0])
        except Exception:
            pass

    def on_start(icon_item, item):
        start_service()
        update_icon_state()

    def on_stop(icon_item, item):
        stop_service()
        update_icon_state()

    def on_restart(icon_item, item):
        restart_service()
        update_icon_state()

    def on_quit(icon_item, item):
        icon.stop()

    def open_control_window(icon_item, item):
        script = PROJECT_ROOT / "tray_control_window.py"
        try:
            subprocess.Popen(
                [sys.executable, str(script)],
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    menu = pystray.Menu(
        pystray.MenuItem("Control (Start/Stop)", open_control_window, default=True),
        pystray.MenuItem("Start", on_start),
        pystray.MenuItem("Stop", on_stop),
        pystray.MenuItem("Restart", on_restart),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit),
    )

    title_running = "Telegram Nick Assistant — running"
    title_stopped = "Telegram Nick Assistant — stopped"

    def get_title():
        return title_running if is_service_active() else title_stopped

    icon = pystray.Icon("telegram_nick_assistant", current_icon[0], get_title(), menu)

    def icon_updater():
        while True:
            time.sleep(2)
            try:
                active = is_service_active()
                new_img = icon_running if active else icon_stopped
                icon.icon = new_img
                icon.title = title_running if active else title_stopped
            except Exception:
                break

    updater = threading.Thread(target=icon_updater, daemon=True)
    updater.start()

    icon.run()


if __name__ == "__main__":
    run_tray()
