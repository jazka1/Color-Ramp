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
source.exclude_dirs = .buildozer,bin,venv,__pycache__

# (str) Application versioning
version = 1.0.1

# (list) Application requirements
requirements = python3,kivy,pillow

# Icon
icon.filename = %(source.dir)s/logo.png

# Orientation
orientation = portrait
fullscreen = 0

# Permissions
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES

# Android API
android.api = 33
android.minapi = 21
android.ndk = 25b

# Android settings
android.allow_backup = True
android.manifest.application_attributes = android:requestLegacyExternalStorage="true"

# Architectures
android.archs = arm64-v8a, armeabi-v7a

# Accept SDK license
android.accept_sdk_license = True

[buildozer]

# **PENTING: Ini yang sering menyebab error kalau salah**
# Gunakan Python 3.9 untuk p4a, bukan 3.10 atau 3.11
python_version = 3.9
android.p4a_python_version = 3.9

# **PENTING: Gunakan p4a release yang sudah stable**
# Jangan gunakan 2022.7.20, gunakan yang lebih lama
android.p4a_release = 2022.7.20

# Gradle dependencies
android.gradle_dependencies = 

# Accept SDK license
android.accept_sdk_license = True

# Logging
log_level = 2
warn_on_root = 1
