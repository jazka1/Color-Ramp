# Color Ramp

<img src="logo.png" width="120" alt="logo Color Ramp">

Aplikasi Android (Kivy/Python) untuk mencari, mendeteksi, dan menyimpan palet warna
dari gambar — lengkap dengan kaca pembesar warna (color magnifier), color detector,
dan tangkapan layar panjang.

[![Build APK](https://github.com/jazka1/Color-Ramp/actions/workflows/build-apk.yml/badge.svg)](https://github.com/jazka1/Color-Ramp/actions/workflows/build-apk.yml)

## Unduh

APK tersedia di halaman **[Releases](https://github.com/jazka1/Color-Ramp/releases)**.

1. Unduh berkas `Color-Willing-<versi>-debug.apk`.
2. Izinkan "Install unknown apps" untuk aplikasi file manager / browser kamu.
3. Pasang APK, lalu buka aplikasi dan izinkan akses media/gambar.

## Fitur

- **Color Detector** — ambil warna dari gambar dan susun palet.
- **Color Magnifier** — perbesar bagian gambar untuk mengambil warna presisi.
- **Long Screenshot** — gabungkan beberapa tangkapan layar menjadi satu gambar panjang.
- **Simpan palet** sebagai gambar ke folder `Pictures/Pallet Color Ramp`.

## Struktur proyek

| Berkas | Keterangan |
| --- | --- |
| `main.py` | Entry point aplikasi Kivy |
| `color_detector.py` | Tab deteksi warna & palet |
| `color_magnifier.py` | Tab kaca pembesar warna |
| `long_screenshot.py` | Fitur tangkapan layar panjang |
| `buildozer.spec` | Konfigurasi build Android |
| `.github/workflows/build-apk.yml` | CI: build APK + rilis otomatis |

## Build & rilis otomatis (GitHub Actions)

Workflow berjalan otomatis pada setiap push ke `main`, dan bisa dijalankan manual
dari tab **Actions → Build APK → Run workflow**.

### Merilis versi baru

```bash
git tag v1.0.2
git push origin v1.0.2
```

Saat tag `v*` di-push, CI akan:

1. menimpa `version` di `buildozer.spec` sesuai tag (`v1.0.2` → `1.0.2`),
2. build APK,
3. membuat GitHub Release dan melampirkan APK-nya.

## Build manual (Linux / WSL)

```bash
sudo apt-get install -y autoconf automake build-essential ccache cmake gettext git \
  libffi-dev libltdl-dev libssl-dev libtool openjdk-17-jdk patch pkg-config \
  python3-pip python3-venv unzip zip zlib1g-dev
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
buildozer -v android debug     # hasil: bin/*.apk
```

## Catatan

- APK yang dihasilkan bertipe **debug** (ditandatangani dengan debug key) sehingga
  bisa langsung dipasang. Untuk Play Store, tambahkan keystore rilis dan gunakan
  `buildozer android release`.
- Pada Android 11+ penulisan langsung ke `Pictures/` dibatasi sistem. Aplikasi akan
  otomatis memakai folder privat aplikasi bila folder publik tidak bisa dibuat.
