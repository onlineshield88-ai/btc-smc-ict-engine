[app]

title = BTC SMC ICT Engine
package.name = btcsmcictengine
package.domain = org.btctrader

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db

version = 1.0

requirements = python3,kivy,plyer,pyjnius,certifi

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,FOREGROUND_SERVICE,WAKE_LOCK,POST_NOTIFICATIONS,RECEIVE_BOOT_COMPLETED
services = Engine:service.py:foreground

android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a

android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
