#!/bin/bash
#
# Install Telegram Nick Assistant: user systemd service (autostart + restart on failure)
# and tray icon (autostart) for Start/Stop control.
# No sudo required - uses systemd --user.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(realpath "$SCRIPT_DIR")"
VENV_BIN="$PROJECT_ROOT/.venv/bin"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
SERVICE_NAME="telegram-nick-assistant"
USER_SYSTEMD="$HOME/.config/systemd/user"
AUTOSTART="$HOME/.config/autostart"

mkdir -p "$USER_SYSTEMD"
mkdir -p "$AUTOSTART"

# Ensure venv exists and has tray deps
if [ ! -x "$VENV_PYTHON" ]; then
    echo "Creating venv and installing dependencies..."
    python3 -m venv "$PROJECT_ROOT/.venv"
    "$VENV_PYTHON" -m pip install -q -r "$PROJECT_ROOT/requirements.txt"
fi
if ! "$VENV_PYTHON" -c "import pystray" 2>/dev/null; then
    echo "Installing tray dependencies (pystray, Pillow)..."
    "$VENV_PYTHON" -m pip install -q pystray Pillow
fi

# Generate and install systemd user service (bash -c for paths with spaces)
sed -e "s|@PROJECT_ROOT@|$PROJECT_ROOT|g" \
    "$PROJECT_ROOT/telegram-nick-assistant.service.in" > "$USER_SYSTEMD/$SERVICE_NAME.service"

echo "Reloading systemd user daemon..."
systemctl --user daemon-reload

echo "Enabling service (autostart at login)..."
systemctl --user enable "$SERVICE_NAME.service"

# Stop any manually run main.py so only one instance runs (avoids session lock)
pkill -f "Telegram Nick Assistant.*main.py" 2>/dev/null || true
rm -f "$PROJECT_ROOT/userbot_session.session-journal" 2>/dev/null || true
sleep 2

echo "Starting service..."
systemctl --user start "$SERVICE_NAME.service" || true

# Tray autostart .desktop
TRAY_DESKTOP="$AUTOSTART/telegram-nick-assistant-tray.desktop"
cat > "$TRAY_DESKTOP" << EOF
[Desktop Entry]
Type=Application
Name=Telegram Nick Assistant Tray
Comment=System tray control for Telegram Nick Assistant
Exec="$VENV_PYTHON" "$PROJECT_ROOT/tray_launcher.py"
Path=$PROJECT_ROOT
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true
EOF
chmod +x "$TRAY_DESKTOP"
echo "Tray autostart: $TRAY_DESKTOP"

echo "Starting tray icon (so it appears now)..."
if [ -n "$DISPLAY" ]; then
    (cd "$PROJECT_ROOT" && nohup "$VENV_PYTHON" tray_launcher.py >/dev/null 2>&1 &)
    echo "  Tray started in background. Check the system tray (near the clock)."
else
    echo "  DISPLAY not set (e.g. SSH). Tray will start at next graphical login."
fi

echo ""
echo "Done."
echo "  - Service: systemctl --user status $SERVICE_NAME"
echo "  - Logs:    journalctl --user -u $SERVICE_NAME -f"
echo "  - Tray:    starts at login; use icon to Start/Stop."
echo "  - To show tray now: $VENV_PYTHON tray_launcher.py"
echo "  - Stop:    systemctl --user stop $SERVICE_NAME"
echo "  - Uninstall: ./uninstall-tray-and-service.sh"
