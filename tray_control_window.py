#!/usr/bin/env python3
"""
Control window: Start/Stop/Refresh for Telegram Nick Assistant.
Opened from tray menu "Control (Start/Stop)" or run: python tray_control_window.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    print("tkinter not available")
    sys.exit(1)

from tray_launcher import is_service_active, start_service, stop_service


def run_control_window():
    root = tk.Tk()
    root.title("Telegram Nick Assistant")
    root.resizable(False, False)
    root.minsize(280, 140)

    frame = ttk.Frame(root, padding=12)
    frame.pack(fill=tk.BOTH, expand=True)

    status_var = tk.StringVar(value="Checking...")

    def refresh_status():
        if is_service_active():
            status_var.set("Status: Running")
        else:
            status_var.set("Status: Stopped")

    def on_start():
        start_service()
        root.after(500, refresh_status)

    def on_stop():
        stop_service()
        root.after(500, refresh_status)

    ttk.Label(frame, text="Telegram Nick Assistant", font=("", 11, "bold")).pack(pady=(0, 8))
    ttk.Label(frame, textvariable=status_var).pack(pady=(0, 12))
    btn_frame = ttk.Frame(frame)
    btn_frame.pack()
    ttk.Button(btn_frame, text="Start", command=on_start).pack(side=tk.LEFT, padx=4)
    ttk.Button(btn_frame, text="Stop", command=on_stop).pack(side=tk.LEFT, padx=4)
    ttk.Button(btn_frame, text="Refresh", command=refresh_status).pack(side=tk.LEFT, padx=4)

    refresh_status()
    root.mainloop()


if __name__ == "__main__":
    run_control_window()
