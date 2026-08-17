[app]

title = Mobile Data App

package.name = mobiledata

package.domain = org.example

source.dir = .

source.include_exts = py,png,jpg,kv,atlas,json,db

version = 1.0.0

requirements = python3,kivy==2.3.0

orientation = portrait

fullscreen = 0


[buildozer]

log_level = 2

warn_on_root = 1

android.api = 33

android.minapi = 24

android.archs = arm64-v8a,armeabi-v7a

android.accept_sdk_license = True
