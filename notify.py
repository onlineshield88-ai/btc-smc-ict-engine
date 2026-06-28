"""
notify.py
Notification helper.
Android APK -> gunakan Plyer.
Termux/Desktop -> hanya print log.
"""

import os

IS_ANDROID = "ANDROID_PRIVATE" in os.environ

def send_notify(message, title_suffix=""):
    if not IS_ANDROID:
        print(f"[NOTIFY] {title_suffix}: {message}")
        return

    try:
        from plyer import notification

        notification.notify(
            title=f"BTC Signal {title_suffix}",
            message=message,
            app_name="BTC SMC ICT Engine",
            timeout=10
        )

    except Exception as e:
        print("[notify]", e)
