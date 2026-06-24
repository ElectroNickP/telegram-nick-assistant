#!/bin/bash
#
# Uninstall Telegram Nick Assistant: stop and disable service, remove tray autostart.
#

set -e

SERVICE_NAME="telegram-nick-assistant"
USER_SYSTEMD="$HOME/.config/systemd/user"
AUTOSTART="$HOME/.config/autostart"

systemctl --user stop "$SERVICE_NAME.service" 2>/dev/null || true
systemctl --user disable "$SERVICE_NAME.service" 2>/dev/null || true
rm -f "$USER_SYSTEMD/$SERVICE_NAME.service"
systemctl --user daemon-reload

rm -f "$AUTOSTART/telegram-nick-assistant-tray.desktop"

echo "Uninstalled. Tray icon will disappear after you close it (or next login)."
