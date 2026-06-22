[app]

title = BTC SMC ICT Engine
package.name = btcsmcictengine
package.domain = org.btctrader

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db

version = 1.0

requirements = python3==3.11.6,kivy==2.2.1,plyer,certifi

orientation = portrait
fullscreen = 0

android.permissions = INTERNET

android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a

android.allow_backup = True

p4a.branch = stable

[buildozer]
log_level = 2
warn_on_root = 1
