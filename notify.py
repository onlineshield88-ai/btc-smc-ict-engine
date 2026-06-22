"""
notify.py
================================================================================
Notifikasi Android saat sinyal BUY/SELL terdeteksi.

Memakai Plyer (library Kivy ekosistem yang membungkus notification API
Android secara native) - berbeda dari versi CLI sebelumnya yang memakai
termux-notification (khusus Termux, tidak akan ada di APK biasa).

Plyer otomatis fallback ke desktop notification saat dites di PC/Mac/Linux,
dan no-op aman jika platform tidak didukung (tidak akan crash app).
================================================================================
"""

def send_notify(message, title_suffix=""):
    """
    Kirim notifikasi sistem. Aman dipanggil di platform apapun -
    jika gagal (mis. permission belum diberikan, atau platform tidak
    didukung plyer), exception ditangkap dan diabaikan agar tidak
    menghentikan service/app.
    """
    try:
        from plyer import notification
        title = f"BTC Signal {title_suffix}".strip()
        notification.notify(
            title=title,
            message=message,
            app_name="BTC SMC ICT Engine",
            timeout=10
        )
    except Exception as e:
        print(f"[notify] gagal kirim notifikasi: {e}")
