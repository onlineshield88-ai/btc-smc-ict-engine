"""
service.py
================================================================================
FOREGROUND SERVICE - berjalan terpisah dari proses UI utama.

Di Android, file ini dijalankan sebagai proses Service tersendiri (didaftarkan
di buildozer.spec sebagai `services = Engine:service.py`). Ini memungkinkan
engine analisa tetap berjalan walau aplikasi di-minimize / user pindah ke
app lain, SELAMA notifikasi foreground masih aktif (wajib oleh Android sejak
Android 8+, supaya OS tidak langsung membunuh proses background).

Foreground service WAJIB menampilkan notifikasi persisten (terlihat di status
bar) selama service berjalan - ini adalah aturan dari Android sendiri, bukan
pilihan desain. Notifikasi ini berbeda dari notifikasi sinyal BUY/SELL.

CATATAN PENTING SOAL "TETAP LIVE DI BACKGROUND" DI ANDROID:
- Android tetap bisa membunuh foreground service dalam kondisi ekstrem
  (RAM sangat rendah, battery saver agresif, OEM tertentu seperti Xiaomi/
  Oppo/Vivo punya battery management sendiri yang lebih agresif dari stock
  Android). Tidak ada cara 100% mencegah ini dari pihak developer app.
- Mitigasi yang disertakan: AlarmManager (lihat restart_alarm.py) menjadwalkan
  ulang servis tiap beberapa menit sebagai fallback jika service terbunuh.
- User WAJIB mengizinkan "Unrestricted battery usage" / mematikan battery
  optimization untuk app ini di Setting Android, agar reliability maksimal.
================================================================================
"""

import time
import traceback
from datetime import datetime

import engine
import db
from notify import send_notify

REFRESH_SECONDS = 20
_last_signal_candle_time = None


def _setup_foreground_notification():
    """
    Tampilkan notifikasi foreground service (wajib oleh Android sejak versi 8+
    agar proses tidak langsung dibunuh OS saat app di background).

    Memakai API resmi python-for-android: PythonService.mService langsung,
    BUKAN 'from android import AndroidService' (API lama/deprecated yang
    referensinya sudah tidak konsisten di versi p4a terbaru).
    """
    try:
        from jnius import autoclass

        PythonService = autoclass("org.kivy.android.PythonService")
        service = PythonService.mService

        # set_autorestart membantu Android merestart service jika diberhentikan
        # paksa oleh sistem (selain mekanisme AlarmManager terpisah di restart_alarm.py)
        try:
            service.setAutoRestartService(True)
        except Exception:
            pass

        return service
    except Exception as e:
        print(f"[service] Bukan di Android atau gagal setup notification: {e}")
        return None


def _update_service_notification(service, text):
    """
    Update teks notifikasi foreground. PythonService Java class menyediakan
    method start() yang juga bisa dipanggil ulang untuk update notifikasi,
    namun cara paling stabil adalah membiarkan teks statis dan hanya
    mengandalkan log - update dinamis notifikasi tiap 20s berisiko boros
    battery/processing untuk OS notification manager. Title/isi notifikasi
    awal sudah cukup informatif (lihat service.start() saat pertama dipanggil
    dari main.py).
    """
    pass


def run_cycle():
    """Satu siklus analisa + simpan history + kirim notifikasi jika ada sinyal baru."""
    global _last_signal_candle_time

    result = engine.run_analysis()

    if result.get("error"):
        print(f"[service] error: {result['error']}")
        return result

    signal = result["signal"]
    candle_time = result["time"]

    if signal != "NO SIGNAL / WAIT":
        saved = db.insert_signal(result)
        if saved and _last_signal_candle_time != candle_time:
            plan = result.get("plan") or {}
            regime = result.get("volatility_regime", "-")
            msg = (
                f"{signal} (score {result['score']}/80) | regime: {regime}\n"
                f"Entry: {plan.get('entry')}  SL: {plan.get('stop_loss')}\n"
                f"TP1: {plan.get('tp1')}  TP2: {plan.get('tp2')}  TP3: {plan.get('tp3')}"
            )
            send_notify(msg, title_suffix=signal)
            _last_signal_candle_time = candle_time

    return result


def main_loop():
    print(f"[service] Engine dimulai: {engine.ENGINE_VERSION}")
    service = _setup_foreground_notification()

    while True:
        try:
            result = run_cycle()
            if not result.get("error"):
                status_text = (
                    f"{result['signal']} | Close {result['close']} | "
                    f"Score {result['score']}/80 | "
                    f"{datetime.now().strftime('%H:%M:%S')}"
                )
            else:
                status_text = f"Error: {result['error']}"

            _update_service_notification(service, status_text)

        except Exception:
            print("[service] EXCEPTION saat run_cycle:")
            traceback.print_exc()

        time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    db.init_db()
    main_loop()
