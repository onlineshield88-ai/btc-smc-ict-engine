[app]

title = BTC SMC ICT Engine
package.name = btcsmcictengine
package.domain = org.btctrader

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db

version = 1.0

requirements = python3,kivy==2.2.1,plyer,pyjnius

orientation = portrait
fullscreen = 0

# icon.filename = %(source.dir)s/data/icon.png
# (sengaja dimatikan dulu - icon custom file binary, susah di-copas via teks.
#  APK pertama akan pakai icon default Kivy. Bisa ditambah belakangan.)

android.permissions = INTERNET,FOREGROUND_SERVICE,WAKE_LOCK,POST_NOTIFICATIONS,RECEIVE_BOOT_COMPLETED

services = Engine:service.py:foreground

android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

android.allow_backup = True
android.gradle_dependencies =

[buildozer]
log_level = 2
warn_on_root = 1
