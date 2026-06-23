[app]
title = BTC SMC ICT Engine
package.name = btcsmcictengine
package.domain = org.btctrader
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 2.0
requirements = python3,kivy==2.3.0,plyer,pyjnius
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,FOREGROUND_SERVICE,WAKE_LOCK,POST_NOTIFICATIONS,RECEIVE_BOOT_COMPLETED
android.api = 33
android.minapi = 24
android.ndk = 25c
android.ndk_api = 24
android.arch = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
