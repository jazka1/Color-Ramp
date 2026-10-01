# color_magnifier.py
# ============================================================
# Halaman 4: Color Magnifier
# Fitur: Upload gambar, lalu sentuh/geser di atas gambar untuk
#        memunculkan kursor kaca pembesar bulat (bergaya sama
#        seperti kursor "+" di Halaman Color Gear > GAMBAR),
#        menampilkan NAMA WARNA dan KODE WARNA (HEX & RGB)
#        secara real-time. Lepas jari untuk menyimpan warna
#        tersebut ke Palet Warna di bawah gambar.
#
# Palet Warna:
# - Kotak BISA DITAMBAH lewat tombol "+" di ujung kanan baris palet.
# - Kotak BISA DIHAPUS lewat tombol "\u2715" kecil di tiap slot
#   (otomatis mengurangi jumlah slot).
# - Kode HEX di tiap slot bisa DIKETUK untuk disalin ke clipboard.
#
# Nama warna & kode warna diambil dari data yang sama dengan
# Halaman 3 (color_detector.py) supaya konsisten di seluruh app.
# ============================================================

import os
import io
import threading
import colorsys

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Line, Ellipse, RoundedRectangle
from kivy.core.image import Image as CoreImage
from kivy.graphics.texture import Texture
from kivy.core.clipboard import Clipboard
from kivy.utils import platform
from kivy.metrics import dp

# Pakai ulang data & fungsi warna dari Halaman 3 supaya nama warna
# & kode warna konsisten dan tidak perlu duplikasi daftar besar.
# Komponen UI flat (FlatButton, add_rounded_card, ACCENT_PURPLE) juga
# dipakai ulang dari sana supaya gaya semua halaman seragam.
from color_detector import (
    find_nearest_color_name, get_color_meaning, HAS_PIL,
    FlatButton, add_rounded_card, ACCENT_PURPLE,
)

if HAS_PIL:
    from PIL import Image as PILImage

THUMB_MAX_SIZE = 240  # resolusi thumbnail di browser "Pilih Gambar" (px)


def _load_thumbnail_texture_async(filepath, on_ready):
    """Buat thumbnail 240px di THREAD LATAR BELAKANG memakai PIL (bukan
    memuat file resolusi penuh), lalu kirim hasilnya (Texture jadi) ke
    main thread lewat Clock. Jauh lebih cepat & ringan daripada
    menampilkan gambar kamera resolusi asli lalu diperkecil tampilannya."""
    def worker():
        data = None
        size = None
        try:
            if HAS_PIL:
                img = PILImage.open(filepath)
                img = img.convert('RGB')
                # img.draft mempercepat decode JPEG secara signifikan
                # dengan langsung meminta ukuran mendekati target.
                try:
                    img.draft('RGB', (THUMB_MAX_SIZE, THUMB_MAX_SIZE))
                except Exception:
                    pass
                img.thumbnail((THUMB_MAX_SIZE, THUMB_MAX_SIZE))
                data = img.tobytes()
                size = img.size
        except Exception:
            data = None
        Clock.schedule_once(lambda dt: on_ready(data, size), 0)

    threading.Thread(target=worker, daemon=True).start()


def _apply_thumbnail_texture(image_widget, data, size):
    if not data or not size:
        return
    try:
        texture = Texture.create(size=size, colorfmt='rgb')
        texture.blit_buffer(data, colorfmt='rgb', bufferfmt='ubyte')
        texture.flip_vertical()
        image_widget.texture = texture
    except Exception:
        pass

PALETTE_START_SLOTS = 6      # jumlah slot kosong di awal
SLOT_HEIGHT = dp(190)
SWATCH_HEIGHT = dp(96)
PALETTE_COLS = 3


# ======================== WIDGET: Kursor Kaca Pembesar =========================
class MagnifierCursor(Widget):
    """
    Lingkaran transparan dengan tanda "+" di tengah -- gayanya sama
    seperti kursor pemilih warna di Halaman Color Gear > GAMBAR.
    Kursor ini TETAP TERLIHAT di posisi terakhir meski jari sudah
    dilepas, sampai pengguna menyentuh titik lain atau memuat gambar
    baru.
    """
    def __init__(self, size_px=90, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(size_px), dp(size_px))
        self.opacity = 0

    def show_color(self, r, g, b):
        self.opacity = 1
        self.canvas.clear()
        with self.canvas:
            Color(r / 255.0, g / 255.0, b / 255.0, 0.55)
            Ellipse(pos=self.pos, size=self.size)
            Color(1, 1, 1, 0.9)
            Line(circle=(self.center_x, self.center_y, self.width / 2 - 1.5), width=2)
            arm = self.width * 0.16
            Color(0.15, 0.15, 0.15, 0.85)
            Line(points=[self.center_x - arm, self.center_y, self.center_x + arm, self.center_y], width=2.4)
            Line(points=[self.center_x, self.center_y - arm, self.center_x, self.center_y + arm], width=2.4)

    def hide(self):
        self.opacity = 0


# ================= WIDGET: Bar Pelangi (hue) =================
class HueBar(Widget):
    """Strip gradasi pelangi horizontal + penanda bulat, murni untuk
    menunjukkan posisi hue dari warna yang sedang terpilih -- gaya
    seperti bar warna di referensi (di bawah gambar)."""
    HUE_STOPS = [
        (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1), (1, 0, 1), (1, 0, 0)
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hue_frac = 0.0  # 0..1 posisi penanda di sepanjang bar
        self._marker_instructions = []
        self.bind(pos=self._redraw_gradient, size=self._redraw_gradient)

    def set_hue_frac(self, frac):
        self.hue_frac = max(0.0, min(1.0, frac))
        self._redraw_marker()

    def _redraw_gradient(self, *_args):
        self.canvas.before.clear()
        w, h = self.size
        x, y = self.pos
        if w <= 0 or h <= 0:
            return
        with self.canvas.before:
            n = len(self.HUE_STOPS) - 1
            seg_w = w / n
            for i in range(n):
                c1 = self.HUE_STOPS[i]
                c2 = self.HUE_STOPS[i + 1]
                steps = 8
                for s in range(steps):
                    t0 = s / steps
                    r = c1[0] + (c2[0] - c1[0]) * t0
                    g = c1[1] + (c2[1] - c1[1]) * t0
                    b = c1[2] + (c2[2] - c1[2]) * t0
                    Color(r, g, b, 1)
                    seg_x = x + i * seg_w + t0 * seg_w
                    Rectangle(pos=(seg_x, y), size=(seg_w / steps + 1, h))
        self._redraw_marker()

    def _redraw_marker(self, *_args):
        for instr in self._marker_instructions:
            self.canvas.after.remove(instr)
        self._marker_instructions.clear()
        w, h = self.size
        x, y = self.pos
        if w <= 0 or h <= 0:
            return
        mx = x + self.hue_frac * w
        my = y + h / 2
        r = h * 0.9
        with self.canvas.after:
            c1 = Color(1, 1, 1, 1)
            e1 = Ellipse(pos=(mx - r, my - r), size=(r * 2, r * 2))
            c2 = Color(0.5, 0.5, 0.55, 1)
            l1 = Line(circle=(mx, my, r), width=dp(1.6))
        self._marker_instructions.extend([c1, e1, c2, l1])


# ================= Image kustom penangkap sentuhan =================
class MagnifierImage(KivyImage):
    """
    KivyImage kustom yang langsung menangkap event sentuh/geser (touch)
    pada dirinya sendiri, lalu memanggil callback dengan posisi sentuh
    dan status ('down' / 'move' / 'up').
    """
    def __init__(self, on_touch_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.on_touch_callback = on_touch_callback
        self._active_touch = None

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._active_touch = touch.uid
            if self.on_touch_callback:
                self.on_touch_callback(touch.pos, 'down')
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            if self.on_touch_callback:
                self.on_touch_callback(touch.pos, 'move')
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self._active_touch = None
            if self.on_touch_callback:
                self.on_touch_callback(touch.pos, 'up')
            return True
        return super().on_touch_up(touch)


# ======================== WIDGET: Slot Palet Warna =========================
class PaletteSlot(BoxLayout):
    """
    Satu slot palet warna (gaya kartu putih, seperti referensi):
    - Terisi -> kotak solid berwarna + kode HEX (ketuk = salin) + ikon
                hapus di sampingnya.
    - Kosong -> kotak garis putus-putus abu + "-".
    Lebar mengikuti kolom grid (bukan lagi lebar tetap untuk scroll
    horizontal) supaya bisa ikut satu scroll vertikal bersama halaman.
    """
    def __init__(self, on_copy=None, on_delete=None, **kwargs):
        super().__init__(orientation='vertical', spacing=dp(8), padding=dp(8),
                          size_hint=(1, None), height=SLOT_HEIGHT, **kwargs)
        self.rgb = None
        self.on_copy = on_copy
        self.on_delete = on_delete
        add_rounded_card(self, bg_rgba=(1, 1, 1, 1), radius=dp(12))

        self.swatch = Widget(size_hint=(1, None), height=SWATCH_HEIGHT)
        self.swatch.bind(pos=self._redraw, size=self._redraw)
        self.add_widget(self.swatch)

        bottom_row = BoxLayout(size_hint=(1, None), height=dp(56), spacing=dp(4))
        self.label_btn = FlatButton(
            text="-", font_size=30, color=(0.35, 0.35, 0.35, 1),
            bg_rgba=(1, 1, 1, 1), border_rgba=(1, 1, 1, 1),
        )
        self.label_btn.bind(on_release=self._on_press)
        bottom_row.add_widget(self.label_btn)

        self.delete_btn = FlatButton(
            text="\U0001F5D1", font_size=32, color=(0.7, 0.15, 0.15, 1),
            bg_rgba=(1, 1, 1, 1), border_rgba=(1, 1, 1, 1),
            size_hint=(None, 1), width=dp(48),
        )
        self.delete_btn.bind(on_release=self._on_delete_press)
        bottom_row.add_widget(self.delete_btn)
        self.add_widget(bottom_row)

        self._redraw()

    def _redraw(self, *args):
        self.swatch.canvas.clear()
        with self.swatch.canvas:
            if self.rgb:
                r, g, b = self.rgb
                Color(r / 255.0, g / 255.0, b / 255.0, 1)
                RoundedRectangle(pos=self.swatch.pos, size=self.swatch.size, radius=[dp(10)])
            else:
                Color(0.75, 0.75, 0.8, 1)
                Line(rounded_rectangle=(self.swatch.x, self.swatch.y, self.swatch.width,
                                         self.swatch.height, dp(10)),
                     dash_length=6, dash_offset=4, width=1.6)

    def set_color(self, rgb):
        self.rgb = rgb
        hex_code = "#{:02X}{:02X}{:02X}".format(*rgb)
        self.label_btn.text = hex_code
        self.label_btn.color = (0.1, 0.1, 0.1, 1)
        self._redraw()

    def clear_color(self):
        self.rgb = None
        self.label_btn.text = "-"
        self.label_btn.color = (0.55, 0.55, 0.55, 1)
        self._redraw()

    def _on_press(self, *args):
        if self.rgb and self.on_copy:
            self.on_copy(self.label_btn.text)

    def _on_delete_press(self, *args):
        if self.on_delete:
            self.on_delete(self)


# ================= WIDGET: Tombol Tambah Slot Palet =================
class AddPaletteSlot(Widget):
    """
    Kotak putus-putus dengan tanda "+" besar -- ketuk untuk menambah
    warna yang SEDANG TAMPIL di readout (hasil sentuh gambar terakhir)
    ke palet. Slot HANYA bertambah lewat tombol ini, tidak lagi
    otomatis saat menggeser/melepas jari di gambar.
    """
    def __init__(self, on_add=None, **kwargs):
        super().__init__(size_hint=(1, None), height=SLOT_HEIGHT, **kwargs)
        self.on_add = on_add
        self.bind(pos=self._redraw, size=self._redraw)
        self._redraw()

    def _redraw(self, *args):
        self.canvas.clear()
        top_y = self.y + self.height - SWATCH_HEIGHT
        with self.canvas:
            Color(0.6, 0.6, 0.65, 1)
            Line(rounded_rectangle=(self.x, top_y, self.width, SWATCH_HEIGHT, dp(14)),
                 dash_length=6, dash_offset=4, width=1.8)
            cx = self.center_x
            cy = top_y + SWATCH_HEIGHT / 2
            arm = dp(20)
            Line(points=[cx - arm, cy, cx + arm, cy], width=3.2)
            Line(points=[cx, cy - arm, cx, cy + arm], width=3.2)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self.on_add:
                self.on_add()
            return True
        return super().on_touch_down(touch)


# ================= WIDGET: Kotak folder/gambar yang bisa disentuh =================
class ButtonBehaviorTile(ButtonBehavior, BoxLayout):
    """BoxLayout biasa yang bisa disentuh -- dipakai untuk bungkus
    thumbnail folder/gambar di browser file buatan sendiri."""
    pass


# ======================== KELAS ColorMagnifierTab =========================
class ColorMagnifierTab(TabbedPanelItem):
    def __init__(self, **kwargs):
        super().__init__(text="Color Magnifier", **kwargs)
        self.pil_image = None          # gambar PIL (RGB) dipakai untuk sampling piksel
        self._last_rgb = None          # warna terakhir yang tersentuh (disimpan saat lepas jari)
        self.palette_slots = []        # daftar PaletteSlot yang sedang ada di palet

        # Root pakai FloatLayout tipis HANYA supaya kursor kaca pembesar
        # bisa "mengambang" di atas gambar (z-order paling akhir), tanpa
        # terpengaruh transformasi scroll dari bagian bawah.
        root = FloatLayout()
        with root.canvas.before:
            Color(0.933, 0.933, 0.945, 1)
            self._page_bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_page_bg, size=self._update_page_bg)
        self.content = root

        main_col = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10),
                              size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        root.add_widget(main_col)

        # --- "Pilih Gambar" -- putih rounded, gaya sama seperti halaman lain ---
        btn_select = FlatButton(text="Pilih Gambar", font_size=26, bold=False,
                                 color=(0.1, 0.1, 0.1, 1),
                                 bg_rgba=(1, 1, 1, 1), border_rgba=(0.8, 0.8, 0.85, 1),
                                 size_hint=(1, None), height=dp(60))
        btn_select.bind(on_release=self.select_image)
        main_col.add_widget(btn_select)

        # --- Kartu gambar (sudut membulat) -- ukuran dikecilkan supaya
        # tidak mendominasi layar dan sisa halaman (info+palet) lega ---
        image_wrap = BoxLayout(size_hint=(1, None), height=dp(240), padding=dp(6))
        add_rounded_card(image_wrap, bg_rgba=(1, 1, 1, 1), radius=dp(16))
        self.image_widget = MagnifierImage(
            on_touch_callback=self._handle_touch,
            keep_ratio=True, allow_stretch=True,
            size_hint=(1, 1)
        )
        image_wrap.add_widget(self.image_widget)
        main_col.add_widget(image_wrap)

        # --- Bar pelangi (hue) tepat di bawah gambar, gaya referensi ---
        self.hue_bar = HueBar(size_hint=(1, None), height=dp(14))
        main_col.add_widget(self.hue_bar)

        # --- Sisanya (info warna + palet) di-scroll terpisah, supaya
        # posisi gambar & kursor kaca pembesar tetap stabil ---
        lower_scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, bar_width=dp(6))
        main_col.add_widget(lower_scroll)
        body = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(12),
                          padding=[0, dp(10), 0, dp(10)])
        body.bind(minimum_height=body.setter('height'))
        lower_scroll.add_widget(body)

        # --- Baris info: swatch kiri + nama (kiri) & hex (kanan) ---
        info_row = BoxLayout(size_hint=(1, None), height=dp(120), spacing=dp(14))
        self.swatch = Widget(size_hint=(0.28, 1))
        with self.swatch.canvas:
            self._swatch_color = Color(0.6, 0.6, 0.6, 1)
            self._swatch_rect = RoundedRectangle(pos=self.swatch.pos, size=self.swatch.size, radius=[dp(14)])
        self.swatch.bind(pos=self._update_swatch, size=self._update_swatch)
        info_row.add_widget(self.swatch)

        name_hex_col = BoxLayout(orientation='vertical', size_hint=(0.72, 1))
        name_hex_row = BoxLayout(size_hint=(1, None), height=dp(50))
        self.name_label = Label(
            text="Sentuh gambar", font_size=32, bold=True, color=(0, 0, 0, 1),
            halign='left', valign='middle', size_hint_x=0.55
        )
        self.name_label.bind(size=lambda l, *a: setattr(l, 'text_size', (l.width, None)))
        self.code_label = Label(
            text="", font_size=28, color=(0.15, 0.15, 0.15, 1),
            halign='right', valign='middle', size_hint_x=0.45
        )
        self.code_label.bind(size=lambda l, *a: setattr(l, 'text_size', (l.width, None)))
        name_hex_row.add_widget(self.name_label)
        name_hex_row.add_widget(self.code_label)
        name_hex_col.add_widget(name_hex_row)
        info_row.add_widget(name_hex_col)
        body.add_widget(info_row)

        # --- Kartu arti warna ---
        meaning_box = BoxLayout(size_hint=(1, None), height=dp(76), padding=[dp(14), dp(8)])
        add_rounded_card(meaning_box, bg_rgba=(0.94, 0.94, 0.97, 1))
        self.meaning_label = Label(text="", font_size=24, color=(0.25, 0.25, 0.25, 1),
                                    halign='left', valign='middle')
        self.meaning_label.bind(size=lambda l, *a: setattr(l, 'text_size', l.size))
        meaning_box.add_widget(self.meaning_label)
        body.add_widget(meaning_box)

        # --- Tombol Hex / Nama / Arti (salin ke clipboard) ---
        copy_box = BoxLayout(size_hint=(1, None), height=dp(64), spacing=dp(10))
        btn_hex = FlatButton(text="Hex", font_size=26, color=(0.1, 0.1, 0.1, 1),
                              bg_rgba=(1, 1, 1, 1), border_rgba=(0.7, 0.7, 0.75, 1))
        btn_hex.bind(on_release=lambda *_a: self._copy_text(self.code_label.text))
        btn_nama = FlatButton(text="Nama", font_size=26, color=(0.1, 0.1, 0.1, 1),
                               bg_rgba=(1, 1, 1, 1), border_rgba=(0.7, 0.7, 0.75, 1))
        btn_nama.bind(on_release=lambda *_a: self._copy_text(self.name_label.text))
        btn_arti = FlatButton(text="Arti", font_size=26, color=(0.1, 0.1, 0.1, 1),
                               bg_rgba=(1, 1, 1, 1), border_rgba=(0.7, 0.7, 0.75, 1))
        btn_arti.bind(on_release=lambda *_a: self._copy_text(self.meaning_label.text))
        copy_box.add_widget(btn_hex)
        copy_box.add_widget(btn_nama)
        copy_box.add_widget(btn_arti)
        body.add_widget(copy_box)

        # --- Nilai Warna (RGB) -- kotak putih bordered, tampilan saja ---
        nilai_title = Label(text="Nilai Warna (RGB)", font_size=30, bold=True, color=(0, 0, 0, 1),
                             size_hint=(1, None), height=dp(38), halign='left', valign='bottom')
        nilai_title.bind(size=lambda l, *a: setattr(l, 'text_size', l.size))
        body.add_widget(nilai_title)

        rgb_row = BoxLayout(size_hint=(1, None), height=dp(70), spacing=dp(10))
        self.r_chip = self._make_value_chip("0")
        self.g_chip = self._make_value_chip("0")
        self.b_chip = self._make_value_chip("0")
        for lbl_text, chip in (("R", self.r_chip), ("G", self.g_chip), ("B", self.b_chip)):
            col = BoxLayout(orientation='vertical', spacing=dp(4))
            head = Label(text=lbl_text, font_size=22, color=(0, 0, 0, 1),
                         size_hint=(1, None), height=dp(26))
            col.add_widget(head)
            col.add_widget(chip)
            rgb_row.add_widget(col)
        body.add_widget(rgb_row)

        self.status_label = Label(
            text="",
            font_size=18,
            color=(0.3, 0.3, 0.3, 1),
            size_hint=(1, None), height=dp(46),
            halign='left',
            valign='middle'
        )
        self.status_label.bind(size=lambda l, *a: setattr(l, 'text_size', (l.width, None)))
        body.add_widget(self.status_label)

        # ---- Palet Warna -- grid yang melipat ke bawah (BUKAN scroll
        # horizontal terpisah lagi), supaya seluruh halaman ini cuma
        # punya SATU arah scroll (vertikal) dan tidak saling rebutan
        # gesture dengan scroll di bawahnya. ----
        palette_title = Label(
            text="Palet Warna (ketuk kode = salin, [] = hapus, + = tambah)",
            font_size=18, color=(0.35, 0.35, 0.35, 1),
            size_hint=(1, None), height=dp(28),
            halign='left', valign='middle'
        )
        palette_title.bind(size=lambda l, *a: setattr(l, 'text_size', (l.width, None)))
        body.add_widget(palette_title)

        self.palette_row = GridLayout(cols=PALETTE_COLS, spacing=dp(12), size_hint=(1, None))
        self.palette_row.bind(minimum_height=self.palette_row.setter('height'))
        body.add_widget(self.palette_row)

        self.add_tile = AddPaletteSlot(on_add=self._commit_current_color)
        for _ in range(PALETTE_START_SLOTS):
            self._add_empty_slot(rebuild=False)
        self._rebuild_palette_row()

        # Kursor kaca pembesar ditambahkan TERAKHIR & langsung ke root
        # supaya selalu tergambar paling atas dan bebas mengambang
        # tepat di titik sentuh tanpa terpengaruh susunan BoxLayout.
        self.cursor = MagnifierCursor(size_px=90)
        root.add_widget(self.cursor)

        if not HAS_PIL:
            self.status_label.text = "\u26A0\uFE0F Modul PIL/Pillow tidak ditemukan \u2014 kaca pembesar butuh Pillow."

    def _update_page_bg(self, *_args):
        self._page_bg.pos = self.content.pos
        self._page_bg.size = self.content.size

    def _make_value_chip(self, text):
        chip = Label(text=text, font_size=28, color=(0.05, 0.05, 0.05, 1),
                      halign='center', valign='middle', size_hint=(1, None), height=dp(56))
        chip.bind(size=lambda l, *a: setattr(l, 'text_size', l.size))
        radius = dp(10)
        with chip.canvas.before:
            Color(0.78, 0.78, 0.82, 1)
            border = Line(rounded_rectangle=(chip.x, chip.y, chip.width, chip.height, radius), width=dp(1.3))
            Color(1, 1, 1, 1)
            fill = RoundedRectangle(pos=(chip.x + dp(1.5), chip.y + dp(1.5)),
                                     size=(chip.width - dp(3), chip.height - dp(3)), radius=[radius])

        def _sync(*_a):
            border.rounded_rectangle = (chip.x, chip.y, chip.width, chip.height, radius)
            fill.pos = (chip.x + dp(1.5), chip.y + dp(1.5))
            fill.size = (chip.width - dp(3), chip.height - dp(3))

        chip.bind(pos=_sync, size=_sync)
        return chip

    def _copy_text(self, text):
        if text:
            Clipboard.copy(text)
            self.status_label.text = f"\U0001F4CB Disalin: {text}"

    # -------------------- Pilih & muat gambar --------------------
    def get_default_path(self):
        if platform == 'android':
            paths = [
                '/storage/emulated/0/DCIM/',
                '/storage/emulated/0/Pictures/',
                '/storage/emulated/0/Download/',
                '/storage/emulated/0/'
            ]
            for p in paths:
                if os.path.exists(p) and os.access(p, os.R_OK):
                    return p
            return '/storage/emulated/0/'
        elif platform == 'win':
            return 'C:/Users/'
        elif platform in ('linux', 'macosx'):
            return os.path.expanduser('~/Pictures/')
        else:
            return os.getcwd()

    def select_image(self, instance):
        # CATATAN: plyer.filechooser di Android build ini terbukti
        # menyebabkan crash/freeze (ActivityResultListener
        # ClassNotFoundException) -- errornya muncul di thread lain
        # sehingga tidak bisa ditangkap oleh try/except di sini, jadi
        # JANGAN dipakai lagi. Langsung pakai browser gambar buatan
        # sendiri (aman, sudah terbukti jalan & ada thumbnail asli).
        self._select_image_kivy_chooser()

    def _on_native_file_selected(self, selection):
        if selection:
            filepath = selection[0]
            Clock.schedule_once(lambda dt: self.load_image(filepath), 0)

    def _select_image_kivy_chooser(self):
        """Browser file buatan sendiri (bukan FileChooserIconView bawaan
        Kivy) supaya file gambar tampil sebagai THUMBNAIL asli (preview
        gambarnya kelihatan), bukan ikon generik."""
        self._browser_popup = None
        self._open_folder_browser(self.get_default_path())

    def _open_folder_browser(self, start_path):
        IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tif', '.tiff')

        root_layout = BoxLayout(orientation='vertical', spacing=dp(6), padding=dp(8))
        path_label = Label(text=start_path, font_size=16, color=(1, 1, 1, 1),
                            size_hint=(1, None), height=dp(30),
                            halign='left', valign='middle', shorten=True)
        path_label.bind(size=lambda l, *a: setattr(l, 'text_size', (l.width, None)))
        root_layout.add_widget(path_label)

        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        grid = GridLayout(cols=3, spacing=dp(8), padding=dp(6), size_hint=(1, None))
        grid.bind(minimum_height=grid.setter('height'))
        scroll.add_widget(grid)
        root_layout.add_widget(scroll)

        btn_box = BoxLayout(size_hint_y=None, height=dp(70), spacing=10)
        btn_cancel = Button(text="Batal", font_size=27)
        btn_box.add_widget(btn_cancel)
        root_layout.add_widget(btn_box)

        popup = Popup(title="Pilih Gambar", content=root_layout, size_hint=(0.95, 0.95))
        btn_cancel.bind(on_press=popup.dismiss)

        state = {'path': start_path}

        def make_tile(label_text, thumb_source, on_press):
            tile = BoxLayout(orientation='vertical', size_hint=(1, None), height=dp(150), spacing=dp(4))
            btn = ButtonBehaviorTile(on_press=on_press)
            if thumb_source:
                # Thumbnail 240px dibuat di background thread (PIL), BUKAN
                # menampilkan file resolusi asli lalu diperkecil tampilan
                # -- jauh lebih cepat & ringan untuk foto kamera yang besar.
                img = KivyImage(size_hint=(1, 1), allow_stretch=True, keep_ratio=True)
                btn.add_widget(img)
                _load_thumbnail_texture_async(
                    thumb_source,
                    lambda data, size, w=img: _apply_thumbnail_texture(w, data, size)
                )
            else:
                # Ikon folder digambar sendiri pakai canvas (BUKAN emoji),
                # supaya tidak jadi kotak putih (tofu box) di HP yang
                # fontnya tidak punya glyph emoji tersebut.
                icon = Widget()

                def _draw_folder(widget, *_a):
                    widget.canvas.clear()
                    w, h = widget.size
                    x, y = widget.pos
                    if w <= 0 or h <= 0:
                        return
                    fw, fh = w * 0.7, h * 0.5
                    fx, fy = x + (w - fw) / 2, y + (h - fh) / 2 - h * 0.05
                    with widget.canvas:
                        Color(0.55, 0.55, 0.6, 1)
                        RoundedRectangle(pos=(fx, fy + fh * 0.15), size=(fw * 0.4, fh * 0.25),
                                          radius=[dp(3)])
                        RoundedRectangle(pos=(fx, fy), size=(fw, fh), radius=[dp(4)])

                icon.bind(pos=_draw_folder, size=_draw_folder)
                btn.add_widget(icon)
            tile.add_widget(btn)
            name_lbl = Label(text=label_text, font_size=26, color=(1, 1, 1, 1),
                              size_hint=(1, None), height=dp(46), shorten=True, shorten_from='right')
            tile.add_widget(name_lbl)
            return tile

        def refresh(path):
            state['path'] = path
            path_label.text = path
            grid.clear_widgets()
            try:
                entries = sorted(os.listdir(path))
            except Exception:
                entries = []

            parent = os.path.dirname(path.rstrip('/'))
            if parent and parent != path:
                grid.add_widget(make_tile("../", None, lambda *_a: refresh(parent)))

            folders = []
            images = []
            for name in entries:
                full = os.path.join(path, name)
                try:
                    if os.path.isdir(full):
                        folders.append((name, full))
                    elif name.lower().endswith(IMAGE_EXTS):
                        images.append((name, full))
                except Exception:
                    continue

            for name, full in folders:
                grid.add_widget(make_tile(name, None, lambda *_a, p=full: refresh(p)))

            # Batasi jumlah thumbnail yang dimuat sekaligus -- folder
            # kamera bisa berisi ratusan foto, kalau semua dibuat
            # sekaligus (walau AsyncImage) tetap membebani memori/CPU.
            MAX_THUMBS = 60
            shown_images = images[:MAX_THUMBS]
            for name, full in shown_images:
                grid.add_widget(make_tile(name, full, lambda *_a, p=full: _pick(p)))
            if len(images) > MAX_THUMBS:
                more_lbl = Label(
                    text="+ {} foto lagi (buka folder lain untuk melihatnya)".format(
                        len(images) - MAX_THUMBS),
                    font_size=14, color=(0.7, 0.7, 0.7, 1),
                    size_hint=(1, None), height=dp(60)
                )
                grid.add_widget(more_lbl)

        def _pick(filepath):
            popup.dismiss()
            self.load_image(filepath)

        refresh(start_path)
        popup.open()

    def load_image(self, filepath):
        if not os.path.exists(filepath):
            self.status_label.text = "\u274C File tidak ditemukan."
            return
        self.status_label.text = "\u23F3 Memuat gambar..."
        self.cursor.hide()

        def _worker():
            try:
                if HAS_PIL:
                    img = PILImage.open(filepath)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    max_size = 1400
                    if img.width > max_size or img.height > max_size:
                        img.thumbnail((max_size, max_size), PILImage.Resampling.LANCZOS)
                    buf = io.BytesIO()
                    img.save(buf, format='PNG')
                    png_bytes = buf.getvalue()

                    def _apply(dt):
                        try:
                            core_img = CoreImage(io.BytesIO(png_bytes), ext='png')
                            self.image_widget.texture = core_img.texture
                            self.pil_image = img
                            self.status_label.text = (
                                f"\u2705 {os.path.basename(filepath)} dimuat \u2014 "
                                f"sentuh gambar untuk cek warna, lepas untuk simpan ke palet."
                            )
                        except Exception as e:
                            self.status_label.text = f"\u274C Gagal memuat gambar: {e}"
                    Clock.schedule_once(_apply, 0)
                else:
                    def _apply_no_pil(dt):
                        try:
                            core_img = CoreImage(filepath)
                            self.image_widget.texture = core_img.texture
                            self.pil_image = None
                            self.status_label.text = (
                                "\u26A0\uFE0F Gambar tampil, tapi kaca pembesar tidak aktif "
                                "karena Pillow tidak tersedia."
                            )
                        except Exception as e:
                            self.status_label.text = f"\u274C Gagal memuat gambar: {e}"
                    Clock.schedule_once(_apply_no_pil, 0)
            except Exception as e:
                err = str(e)

                def _err(dt):
                    self.status_label.text = f"\u274C Gagal memuat gambar: {err}"
                Clock.schedule_once(_err, 0)

        threading.Thread(target=_worker, daemon=True).start()

    # -------------------- Kaca pembesar (sentuh & geser) --------------------
    def _handle_touch(self, pos, event):
        if self.pil_image is None:
            return

        if event == 'up':
            # Jari dilepas -> TIDAK menyimpan otomatis ke palet lagi.
            # Kursor TIDAK disembunyikan; tetap terlihat di titik terakhir.
            # Untuk menyimpan warna ini ke palet, ketuk tombol "+" di
            # bawah gambar.
            return

        x, y = pos
        img_w, img_h = self.image_widget.norm_image_size
        if img_w <= 0 or img_h <= 0:
            return

        img_x = self.image_widget.center_x - img_w / 2
        img_y = self.image_widget.center_y - img_h / 2

        if not (img_x <= x <= img_x + img_w and img_y <= y <= img_y + img_h):
            return

        fx = (x - img_x) / img_w
        fy_from_top = 1 - ((y - img_y) / img_h)

        pw, ph = self.pil_image.size
        px = min(pw - 1, max(0, int(fx * pw)))
        py = min(ph - 1, max(0, int(fy_from_top * ph)))

        r, g, b = self.pil_image.getpixel((px, py))[:3]
        self._last_rgb = (r, g, b)
        self._show_color(r, g, b)

        cursor_w, cursor_h = self.cursor.size
        self.cursor.pos = (x - cursor_w / 2, y - cursor_h / 2)
        self.cursor.show_color(r, g, b)

    def _show_color(self, r, g, b):
        hex_code = "#{:02X}{:02X}{:02X}".format(r, g, b)
        name = find_nearest_color_name(hex_code)
        meaning = get_color_meaning(name)
        self._swatch_color.rgba = (r / 255.0, g / 255.0, b / 255.0, 1)
        self.name_label.text = name
        self.code_label.text = hex_code
        self.meaning_label.text = meaning
        self.r_chip.text = str(r)
        self.g_chip.text = str(g)
        self.b_chip.text = str(b)
        h, _s, _v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        self.hue_bar.set_hue_frac(h)

    def _update_swatch(self, instance, value):
        self._swatch_rect.pos = instance.pos
        self._swatch_rect.size = instance.size

    # -------------------- Palet warna: tambah / hapus / isi --------------------
    def _rebuild_palette_row(self):
        self.palette_row.clear_widgets()
        for slot in self.palette_slots:
            self.palette_row.add_widget(slot)
        self.palette_row.add_widget(self.add_tile)

    def _add_empty_slot(self, rebuild=True):
        slot = PaletteSlot(on_copy=self._on_slot_copy, on_delete=self._delete_slot)
        self.palette_slots.append(slot)
        if rebuild:
            self._rebuild_palette_row()
        return slot

    def _delete_slot(self, slot):
        if slot in self.palette_slots:
            self.palette_slots.remove(slot)
            self._rebuild_palette_row()

    def _push_palette_color(self, rgb):
        empty_slot = next((s for s in self.palette_slots if s.rgb is None), None)
        if empty_slot is None:
            empty_slot = self._add_empty_slot()
        empty_slot.set_color(rgb)

    def _commit_current_color(self):
        """Dipanggil saat tombol '+' ditekan: ambil warna yang sedang
        tampil di readout (hasil sentuhan terakhir) lalu simpan ke
        palet (mengisi slot kosong pertama, atau menambah slot baru
        kalau semua sudah terisi)."""
        if self._last_rgb is None:
            self.status_label.text = "\u26A0\uFE0F Sentuh gambar dulu untuk memilih warna sebelum menambah ke palet."
            return
        self._push_palette_color(self._last_rgb)

    def _on_slot_copy(self, hex_code):
        Clipboard.copy(hex_code)
        self.status_label.text = f"\U0001F4CB Kode {hex_code} disalin ke clipboard."
