# long_screenshot.py
# ============================================================
# Fitur "Export Tampilan Penuh" (pengganti screenshot panjang)
# untuk aplikasi Kivy.
#
# LATAR BELAKANG / KENAPA FILE INI DIPERLUKAN:
# Fitur screenshot-panjang bawaan HP (mis. MIUI, scroll capture
# di HP Android lain) bekerja dengan cara membaca STRUKTUR WIDGET
# asli Android (RecyclerView / NestedScrollView / WebView) lewat
# Accessibility Service, lalu sistem sendiri yang menggeser widget
# itu sambil memotretnya tahap demi tahap.
#
# Aplikasi Kivy TIDAK memakai widget Android sama sekali -- seluruh
# tampilan (termasuk ScrollView versi Kivy) dirender ke SATU
# permukaan OpenGL (GLSurfaceView). Dari sudut pandang Android, app
# Kivy cuma terlihat sebagai satu gambar polos, bukan struktur
# widget yang bisa "dibaca" -- makanya fitur screenshot panjang
# bawaan HP selalu berhenti / bilang "sudah sampai dasar" walau
# konten aslinya masih panjang.
#
# SOLUSI DI FILE INI:
# Kita export sendiri dari DALAM aplikasi, tidak bergantung fitur
# OS sama sekali. Kuncinya: widget KONTEN di dalam sebuah ScrollView
# selalu berukuran PENUH (seluruh tinggi konten), walau yang
# tampil di layar cuma sepotong. Kivy punya method bawaan
# `Widget.export_to_png()` yang me-render ulang sebuah widget
# SESUAI UKURAN ASLINYA (bukan sesuai area yang sedang terlihat di
# layar) ke sebuah file PNG.
#
# CATATAN PENTING soal warna latar:
# Widget yang di-export SENDIRIAN (lepas dari induknya) TIDAK ikut
# membawa warna latar milik induknya -- yang ter-render cuma yang
# benar-benar digambar di widget itu sendiri. Kalau widget itu
# sendiri tidak punya instruksi canvas untuk mengecat latar, hasil
# PNG-nya akan TRANSPARAN di bagian itu (sering tampil hitam di
# viewer gambar biasa). Karena itu semua fungsi export di file ini
# mengisi latar (default: putih) secara eksplisit saat menyimpan.
#
# ADA 2 MODE EXPORT:
#
# 1) SATU widget/ScrollView saja (export_full_scrollview /
#    make_export_button) -- cocok kalau seluruh halaman memang ada
#    di dalam satu ScrollView.
#
# 2) GABUNGAN beberapa widget disusun vertikal (export_widgets_stacked
#    / make_export_button_multi) -- cocok kalau sebagian halaman
#    TETAP terlihat (tidak ikut discroll, mis. kotak warna & slider
#    Value) dan sebagian lagi ada DI DALAM ScrollView -- semuanya
#    digabung jadi satu gambar utuh dari atas sampai bawah.
# ============================================================

import os
import time

from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.utils import platform

try:
    from PIL import Image as PILImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def _get_output_dir():
    """Folder tujuan simpan hasil export, disesuaikan platform."""
    if platform == 'android':
        try:
            from android.storage import primary_external_storage_path  # type: ignore
            base = primary_external_storage_path()
            out_dir = os.path.join(base, 'Pictures', 'ColorPickerPro')
        except Exception:
            out_dir = '/storage/emulated/0/Pictures/ColorPickerPro'
    else:
        out_dir = os.path.join(os.path.expanduser('~'), 'ColorPickerPro_Export')

    os.makedirs(out_dir, exist_ok=True)
    return out_dir


# ======================== MODE 1: satu ScrollView ========================
def export_full_scrollview(scrollview, filename=None, callback=None, error_callback=None):
    """
    Export SELURUH konten sebuah ScrollView (termasuk bagian yang
    belum pernah di-scroll / belum pernah terlihat di layar) menjadi
    SATU file PNG utuh dari atas sampai bawah.

    scrollview      : instance kivy.uix.scrollview.ScrollView
    filename        : nama file opsional (tanpa folder). Kalau
                       kosong, dibuat otomatis pakai timestamp.
    callback        : dipanggil dengan (filepath) kalau berhasil.
    error_callback  : dipanggil dengan (pesan_error) kalau gagal.
    """
    try:
        if not scrollview.children:
            raise ValueError("ScrollView belum punya konten untuk di-export.")

        content_widget = scrollview.children[0]

        full_w, full_h = content_widget.size
        if full_w <= 0 or full_h <= 0:
            raise ValueError(
                "Ukuran konten tidak valid (widget mungkin belum selesai dirender, "
                "coba lagi setelah halaman selesai dimuat)."
            )

        out_dir = _get_output_dir()
        if not filename:
            filename = f"export_{int(time.time())}.png"
        if not filename.lower().endswith('.png'):
            filename += '.png'
        filepath = os.path.join(out_dir, filename)

        content_widget.export_to_png(filepath)

        if callback:
            Clock.schedule_once(lambda dt: callback(filepath), 0)
        return filepath

    except Exception as e:
        err_msg = str(e)
        if error_callback:
            Clock.schedule_once(lambda dt: error_callback(err_msg), 0)
        else:
            raise
        return None


def make_export_button(scrollview, text="\U0001F4F8 Export Tampilan Penuh (PNG)",
                        on_status=None, **kwargs):
    """
    Widget tombol siap pakai: sekali tekan langsung meng-export
    seluruh konten sebuah ScrollView ke satu file PNG utuh.

    scrollview : ScrollView yang mau di-export kontennya.
    on_status  : fungsi opsional dipanggil dengan teks status
                 (mis. untuk ditampilkan di sebuah Label), contoh:
                     on_status=lambda msg: setattr(self.status_label, 'text', msg)
    **kwargs   : diteruskan ke Button (font_size, size_hint, dll).
    """
    btn = Button(text=text, **kwargs)

    def _on_press(instance):
        if on_status:
            on_status("\u23F3 Membuat gambar tampilan penuh...")

        def _ok(path):
            if on_status:
                on_status(f"\u2705 Tersimpan di: {path}")

        def _err(msg):
            if on_status:
                on_status(f"\u274C Gagal export: {msg}")

        Clock.schedule_once(
            lambda dt: export_full_scrollview(scrollview, callback=_ok, error_callback=_err),
            0.05
        )

    btn.bind(on_press=_on_press)
    return btn


# ================= MODE 2: gabungan beberapa widget (tetap + scroll) =================
def export_widgets_stacked(widgets, filename=None, callback=None, error_callback=None,
                            bg_rgba=(1, 1, 1, 1)):
    """
    Export BEBERAPA widget sekaligus, disusun VERTIKAL dari atas ke
    bawah, jadi SATU file PNG utuh -- berguna untuk menggabungkan
    bagian yang tetap terlihat (tidak ikut scroll, mis. kotak warna
    & slider Value di Halaman 1) dengan bagian yang ada di dalam
    ScrollView, supaya hasil export terlihat sebagai satu halaman
    utuh dari atas sampai bawah (persis tujuan screenshot panjang).

    widgets   : list widget, URUT dari yang paling atas ke paling
                bawah, misal:
                    [color_square, value_layout, scroll_content_widget]
    bg_rgba   : warna latar (RGBA, nilai 0..1) buat mengisi area
                transparan tiap widget & selisih lebar antar potongan.
                Default putih.
    """
    if not HAS_PIL:
        msg = "Gabung beberapa bagian gambar butuh Pillow (PIL), tapi modul itu tidak ditemukan."
        if error_callback:
            Clock.schedule_once(lambda dt: error_callback(msg), 0)
        return None

    try:
        out_dir = _get_output_dir()
        temp_paths = []
        for i, w in enumerate(widgets):
            if w is None or w.size[0] <= 0 or w.size[1] <= 0:
                continue
            tmp_path = os.path.join(out_dir, f"_tmp_export_part_{i}_{int(time.time() * 1000)}.png")
            w.export_to_png(tmp_path)
            temp_paths.append(tmp_path)

        if not temp_paths:
            raise ValueError("Tidak ada widget dengan ukuran valid untuk di-export.")

        images = [PILImage.open(p).convert("RGBA") for p in temp_paths]
        total_w = max(im.width for im in images)
        total_h = sum(im.height for im in images)

        bg = tuple(int(c * 255) for c in bg_rgba[:3]) + (255,)
        combined = PILImage.new("RGBA", (total_w, total_h), bg)

        y_offset = 0
        for im in images:
            # Rata KIRI (x_offset selalu 0), BUKAN ditengahkan --
            # supaya posisi tiap potongan persis seperti di layar asli
            # (semua elemen di app ini rata kiri mulai dari x=0, jadi
            # menengahkan potongan yang lebih sempit justru membuatnya
            # tergeser ke kanan dibanding aslinya).
            x_offset = 0
            layer = PILImage.new("RGBA", (im.width, im.height), bg)
            layer.alpha_composite(im)
            combined.paste(layer, (x_offset, y_offset))
            y_offset += im.height

        if not filename:
            filename = f"export_{int(time.time())}.png"
        if not filename.lower().endswith('.png'):
            filename += '.png'
        out_path = os.path.join(out_dir, filename)
        combined.convert("RGB").save(out_path, format='PNG')

        for p in temp_paths:
            try:
                os.remove(p)
            except Exception:
                pass

        if callback:
            Clock.schedule_once(lambda dt: callback(out_path), 0)
        return out_path

    except Exception as e:
        err_msg = str(e)
        if error_callback:
            Clock.schedule_once(lambda dt: error_callback(err_msg), 0)
        else:
            raise
        return None


def make_export_button_multi(widgets, text="\U0001F4F8 Export Tampilan Penuh (PNG)",
                              on_status=None, bg_rgba=(1, 1, 1, 1), **kwargs):
    """
    Sama seperti make_export_button, tapi untuk kasus halaman yang
    punya bagian TETAP (tidak ikut scroll) + bagian DI DALAM
    ScrollView -- keduanya digabung jadi satu gambar utuh.

    widgets bisa berupa:
      - list widget langsung, urut atas ke bawah, ATAU
      - fungsi tanpa argumen yang MENGEMBALIKAN list widget (dipanggil
        saat tombol ditekan, bukan saat tombol dibuat) -- berguna
        kalau sebagian widget (mis. tab strip) baru tersedia SETELAH
        tombol ini dibuat.

    Contoh (list langsung):
        btn = make_export_button_multi(
            [self.color_square, self.value_layout, self.scroll_content],
            on_status=self.set_status,
        )

    Contoh (lazy, widget-nya ditentukan belakangan):
        btn = make_export_button_multi(
            lambda: [self.tab_strip_widget, self.color_square,
                     self.value_layout, self.scroll_content],
            on_status=self.set_status,
        )
    """
    btn = Button(text=text, **kwargs)

    def _on_press(instance):
        if on_status:
            on_status("\u23F3 Membuat gambar tampilan penuh...")

        def _ok(path):
            if on_status:
                on_status(f"\u2705 Tersimpan di: {path}")

        def _err(msg):
            if on_status:
                on_status(f"\u274C Gagal export: {msg}")

        def _do_export(dt):
            resolved = widgets() if callable(widgets) else widgets
            export_widgets_stacked(resolved, callback=_ok, error_callback=_err, bg_rgba=bg_rgba)

        Clock.schedule_once(_do_export, 0.05)

    btn.bind(on_press=_on_press)
    return btn
