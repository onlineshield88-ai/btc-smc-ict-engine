"""
restart_alarm.py
================================================================================
Mekanisme fallback: AlarmManager Android (diakses via pyjnius) untuk
menjadwalkan ulang foreground service jika ia terbunuh oleh sistem
(Doze mode, battery saver agresif OEM, RAM rendah, dll).

Ini BUKAN WorkManager (yang adalah API AndroidX/Jetpack untuk Kotlin/Java
native dan tidak punya binding resmi di python-for-android). AlarmManager
adalah API Android level lebih rendah yang BISA diakses dari Kivy lewat
pyjnius.

CATATAN JUJUR SOAL KETERBATASAN PENDEKATAN INI:
AlarmManager Android secara native dirancang untuk memicu BroadcastReceiver,
dan BroadcastReceiver custom HARUS berupa class Java/Kotlin yang di-compile,
tidak bisa ditulis sebagai Python murni tanpa menambah source Java custom ke
project buildozer (kompleksitas build signifikan, di luar scope yang bisa
saya sediakan & uji di sini).

PENDEKATAN YANG DIPAKAI SEBAGAI GANTINYA (100% Python, bisa di-build dengan
buildozer standar tanpa custom Java):
  service.start_service() dipanggil ulang via PendingIntent.getService()
  langsung menuju Service Python (PythonService) yang sudah didaftarkan
  python-for-android secara otomatis dari buildozer.spec (services = ...).
  Ini valid karena PythonService adalah Java class bawaan p4a yang sudah
  ter-compile, kita hanya mengarahkan Intent ke sana - bukan membuat
  Receiver baru.

Dipanggil dari main.py saat app pertama dibuka, untuk menjadwalkan
"start ulang service" berkala sebagai jaring pengaman.
================================================================================
"""


def schedule_restart_check(interval_minutes=15):
    """
    Jadwalkan alarm berulang yang akan memanggil ulang start service Python
    (PythonService bawaan python-for-android). Jika service sudah berjalan,
    panggilan ulang ini aman/no-op secara efektif (Android tidak start
    instance kedua untuk service yang sama). Jika service sudah mati,
    panggilan ini akan menghidupkannya kembali.
    No-op aman di platform non-Android (mis. saat dites di desktop).
    """
    try:
        from jnius import autoclass, cast
        from android import mActivity

        Context = autoclass("android.content.Context")
        AlarmManager = autoclass("android.app.AlarmManager")
        Intent = autoclass("android.content.Intent")
        PendingIntent = autoclass("android.app.PendingIntent")
        SystemClock = autoclass("android.os.SystemClock")

        activity = mActivity
        alarm_manager = cast(
            "android.app.AlarmManager",
            activity.getSystemService(Context.ALARM_SERVICE)
        )

        package_name = activity.getPackageName()
        # Target PythonService bawaan p4a, BUKAN custom Receiver.
        # Nama class persis ini di-generate otomatis oleh buildozer saat
        # build dari entry "services = Engine:service.py" di buildozer.spec.
        service_class_name = package_name + ".ServiceEngine"

        intent = Intent()
        intent.setClassName(package_name, service_class_name)

        pending_intent = PendingIntent.getService(
            activity, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT
        )

        interval_ms = interval_minutes * 60 * 1000
        trigger_at = SystemClock.elapsedRealtime() + interval_ms

        alarm_manager.setInexactRepeating(
            AlarmManager.ELAPSED_REALTIME_WAKEUP,
            trigger_at,
            interval_ms,
            pending_intent
        )
        print(f"[restart_alarm] Alarm restart-check terjadwal setiap {interval_minutes} menit")
        return True

    except Exception as e:
        print(f"[restart_alarm] Tidak bisa menjadwalkan alarm (mungkin bukan di Android): {e}")
        return False


def cancel_restart_check():
    """Batalkan alarm restart-check (mis. saat user menekan tombol Stop Engine)."""
    try:
        from jnius import autoclass, cast
        from android import mActivity

        Context = autoclass("android.content.Context")
        AlarmManager = autoclass("android.app.AlarmManager")
        Intent = autoclass("android.content.Intent")
        PendingIntent = autoclass("android.app.PendingIntent")

        activity = mActivity
        alarm_manager = cast(
            "android.app.AlarmManager",
            activity.getSystemService(Context.ALARM_SERVICE)
        )

        package_name = activity.getPackageName()
        service_class_name = package_name + ".ServiceEngine"
        intent = Intent()
        intent.setClassName(package_name, service_class_name)
        pending_intent = PendingIntent.getService(
            activity, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT
        )

        alarm_manager.cancel(pending_intent)
        print("[restart_alarm] Alarm restart-check dibatalkan")
        return True

    except Exception as e:
        print(f"[restart_alarm] Gagal membatalkan alarm: {e}")
        return False
