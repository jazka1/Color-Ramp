[app]

# (str) Title of your application
title = Color Willing

# (str) Package name (huruf kecil, tanpa spasi)
package.name = colorwilling

# (str) Package domain
package.domain = org.jazka

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,otf,json

# (list) List of exclusions
source.exclude_dirs = .buildozer,bin,dist,build,.git,.github,.venv,venv,__pycache__,.idea

# (list) Pattern (glob) yang tidak perlu ikut dibungkus ke dalam APK
source.exclude_patterns = *.apk,*.aab,*.zip,*.pyc,*.log,*.md

# (str) Application versioning
# Catatan: kalau workflow dijalankan dari tag (mis. v1.0.2), nilai ini otomatis
# ditimpa oleh versi tag tersebut.
version = 1.0.1

# (list) Application requirements
# plyer dipakai di main.py (from plyer import filechooser) tapi sebelumnya belum
# didaftarkan, sehingga APK crash saat memilih folder simpan.
# pyjnius dibutuhkan modul android.permissions / android.storage.
requirements = python3,kivy==2.3.1,pillow,plyer,pyjnius

# Buildozer selalu meng-clone p4a sendiri (versi dari pip diabaikan), jadi versi
# p4a WAJIB dipin di sini. Tag v2024.01.21 mem-build Python 3.11.5 (cocok dengan
# Kivy 2.3.1 + Cython 0.29.x). Jangan diganti ke master/2026.x.
p4a.branch = v2024.01.21

# Icon
icon.filename = %(source.dir)s/logo.png

# Orientation
orientation = portrait
fullscreen = 0

# Permissions
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES

# Android API
# Nilai di bawah mengikuti rekomendasi python-for-android 2024.1.21
# (NDK 25b, Python target 3.11.5). Jangan diganti ke NDK 28c selama p4a
# masih versi 2024.x.
android.api = 33
android.minapi = 23
android.ndk_api = 23
android.ndk = 25b

# Android settings
android.allow_backup = True
# Catatan: requestLegacyExternalStorage hanya berlaku untuk targetSdk <= 29,
# jadi tidak lagi berpengaruh di android.api = 34. Key yang benar (kalau butuh
# atribut tambahan di <application>) adalah seperti contoh di bawah:
# android.extra_manifest_application_arguments = android:requestLegacyExternalStorage="true"

# Architectures
android.archs = arm64-v8a, armeabi-v7a

# Accept SDK license
android.accept_sdk_license = True

[buildozer]

# Logging
log_level = 2
warn_on_root = 1
