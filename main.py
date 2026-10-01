from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.slider import Slider
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.spinner import Spinner
from kivy.uix.image import Image
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.core.clipboard import Clipboard
from kivy.graphics import Color, Rectangle, Ellipse, Line, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.uix.behaviors import ButtonBehavior
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform
from kivy.metrics import dp
import math
import random
import os
import json
import weakref
from color_detector import ColorDetectorTab   # import dari file terpisah
from color_magnifier import ColorMagnifierTab  # Halaman 4: kaca pembesar warna
from long_screenshot import make_export_button_multi  # fitur "Export Tampilan Penuh" (pengganti screenshot panjang)

Window.clearcolor = (1, 1, 1, 1)


class AppState:
    """
    Auto-save/auto-load ringan berbasis JSON untuk menyimpan kerjaan
    terakhir user (warna terpilih di Halaman 1, palet & harmoni di
    Halaman 2) agar tidak reset saat aplikasi ditutup lalu dibuka lagi.
    Disimpan di folder data aplikasi (App.user_data_dir) supaya aman
    dipakai di Pydroid3, Termux, maupun APK Android biasa.
    """
    _path = None

    @classmethod
    def get_path(cls):
        if cls._path is None:
            data_dir = None
            try:
                app = App.get_running_app()
                if app is not None:
                    data_dir = app.user_data_dir
            except Exception:
                data_dir = None
            if not data_dir:
                data_dir = os.getcwd()
            try:
                if not os.path.exists(data_dir):
                    os.makedirs(data_dir, exist_ok=True)
            except Exception:
                data_dir = os.getcwd()
            cls._path = os.path.join(data_dir, 'colorfinder_state.json')
        return cls._path

    @classmethod
    def load_all(cls):
        path = cls.get_path()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    @classmethod
    def load_section(cls, section, default=None):
        full = cls.load_all()
        val = full.get(section)
        return val if val is not None else (default if default is not None else {})

    @classmethod
    def save_section(cls, section, data):
        path = cls.get_path()
        try:
            full = cls.load_all()
        except Exception:
            full = {}
        full[section] = data
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(full, f)
        except Exception:
            pass


class GridSettings:
    """
    Menyimpan pengaturan jumlah kolom (cols) & baris (rows) untuk SEMUA
    kotak warna hue-saturation di aplikasi (Halaman 1 & Halaman 2), agar
    semuanya otomatis mengikuti pengaturan "Grid Warna" di Halaman 1.
    """
    cols = 72
    rows = 15
    _listeners = weakref.WeakSet()

    @classmethod
    def register(cls, widget):
        cls._listeners.add(widget)
        try:
            widget.set_grid(cls.cols, cls.rows)
        except Exception:
            pass

    @classmethod
    def update(cls, cols, rows):
        cls.cols = cols
        cls.rows = rows
        for widget in list(cls._listeners):
            try:
                widget.set_grid(cols, rows)
            except Exception:
                pass


# Fungsi untuk meminta izin
def request_storage_permissions():
    if platform != 'android':
        return
    try:
        from android.permissions import request_permissions, Permission
        request_permissions([
            Permission.READ_EXTERNAL_STORAGE,
            Permission.WRITE_EXTERNAL_STORAGE,
            Permission.MANAGE_EXTERNAL_STORAGE
        ])
    except ImportError:
        pass

# ======================== DATA WARNA =========================
COLOR_MEANINGS = {
    "Merah": "Energi, gairah, cinta, keberanian, kekuatan, bahaya",
    "Hijau": "Alam, kesegaran, pertumbuhan, harapan, kesehatan, kedamaian",
    "Biru": "Ketenangan, kepercayaan, stabilitas, kesetiaan, kebijaksanaan",
    "Kuning": "Kebahagiaan, optimisme, kecerdasan, kehangatan, peringatan",
    "Cyan": "Kebebasan, kedamaian, kreativitas, kejernihan, teknologi",
    "Magenta": "Spiritualitas, kasih sayang, harmoni, transformasi",
    "Putih": "Kesucian, kebersihan, kesederhanaan, kepolosan, awal baru",
    "Hitam": "Kekuatan, elegan, misteri, otoritas, kemewahan",
    "Abu-abu": "Netral, keseimbangan, kebijaksanaan, konservatif",
    "Oranye": "Antusiasme, kreativitas, keberanian, kesuksesan, energi",
    "Pink": "Kelembutan, cinta, romantisme, kelembutan, feminin",
    "Ungu": "Kebangsawanan, spiritualitas, misteri, imajinasi, kemewahan",
    "Coklat": "Stabilitas, keandalan, kenyamanan, kesederhanaan",
    "Navy": "Kewibawaan, kepercayaan, tradisi, kedalaman",
    "Teal": "Kedamaian, kejernihan, pemulihan, keseimbangan",
    "Olive": "Kedamaian, kebijaksanaan, alam, ketahanan",
    "Maroon": "Kekuatan, gairah, keanggunan, keberanian",
    "Silver": "Modern, kecanggihan, kemewahan, keanggunan",
    "Lime": "Energi, kesegaran, kegembiraan, vitalitas",
    "Aqua": "Ketenangan, kesegaran, inspirasi, kedamaian",
    "Fuchsia": "Keberanian, gairah, individualitas, keyakinan",
    "Biru Muda": "Ketenangan, kejernihan, kedamaian, kepercayaan",
    "Hijau Muda": "Kesegaran, harapan, pertumbuhan, alam",
    "Krem": "Kelembutan, kenyamanan, kehangatan, klasik",
    "Salem": "Keberanian, gairah, kehangatan, semangat",
    "Toska": "Kedamaian, keseimbangan, kejernihan, ketenangan",
    "Lavender": "Kelembutan, ketenangan, spiritualitas, kemewahan",
    "Emas": "Kekayaan, kemakmuran, kebijaksanaan, kejayaan",
    "Coral": "Kehangatan, gairah, semangat, optimisme",
    "Indigo": "Intuisi, spiritualitas, kebijaksanaan, persepsi",
    "Salmon": "Kehangatan, keramahan, energi, kegembiraan",
    "Tomat": "Gairah, keberanian, semangat, kegembiraan",
    "Ruby": "Gairah, cinta, kekuatan, kemewahan",
    "Sapphire": "Kebijaksanaan, kesetiaan, kebenaran, kepercayaan",
    "Amber": "Energi, keberanian, kreativitas, kehangatan",
    "Jade": "Kedamaian, harmoni, keseimbangan, kemakmuran",
    "Turquoise": "Ketenangan, perlindungan, kreativitas, komunikasi",
    "Perak": "Modern, kecanggihan, keanggunan, teknologi",
    "Platinum": "Kemewahan, eksklusivitas, keanggunan, kebijaksanaan",
    "Rose": "Kelembutan, cinta, romantisme, kehangatan",
    "Apricot": "Kehangatan, optimisme, kreativitas, kegembiraan",
    "Peach": "Kelembutan, keramahan, kehangatan, kebahagiaan",
    "Cinnamon": "Kehangatan, kenyamanan, tradisi, ketenangan",
    "Chocolate": "Kenyamanan, keandalan, kehangatan, kemewahan",
    "Coffee": "Kenyamanan, keandalan, tradisi, kehangatan",
    "Tan": "Keandalan, kesederhanaan, kenyamanan, alam",
    "Beige": "Netral, kenyamanan, keandalan, kesederhanaan",
    "Ivory": "Kesucian, keanggunan, kemewahan, kesederhanaan",
    "Bone": "Kesederhanaan, keandalan, kenyamanan, netral",
    "Wheat": "Kehangatan, kenyamanan, kesederhanaan, alam",
    "Moccasin": "Kehangatan, kenyamanan, tradisi, keandalan",
    "Navajo": "Kehangatan, tradisi, kenyamanan, alam",
    "Cornsilk": "Kehangatan, kenyamanan, kesederhanaan, optimisme",
    "Blonde": "Kehangatan, kecerahan, optimisme, kegembiraan",
    "Honey": "Kehangatan, kemanisan, kebahagiaan, kemakmuran",
    "Gold": "Kekayaan, kemakmuran, kebijaksanaan, kejayaan",
    "Bronze": "Kekuatan, keandalan, kehangatan, kemewahan",
    "Copper": "Kehangatan, kekuatan, energi, kreativitas",
    "Rust": "Kehangatan, keberanian, ketahanan, tradisi",
    "Terra Cotta": "Kehangatan, kenyamanan, alam, tradisi",
    "Sienna": "Kehangatan, ketahanan, alam, kesederhanaan",
    "Umber": "Keandalan, kenyamanan, alam, ketenangan",
    "Burgundy": "Kemewahan, gairah, kekuatan, tradisi",
    "Wine": "Kemewahan, gairah, keanggunan, tradisi",
    "Mauve": "Kelembutan, ketenangan, spiritualitas, kemewahan",
    "Orchid": "Kelembutan, kemewahan, spiritualitas, keanggunan",
    "Plum": "Kemewahan, spiritualitas, keanggunan, kebijaksanaan",
    "Violet": "Spiritualitas, kebijaksanaan, kemewahan, imajinasi",
    "Lilac": "Kelembutan, ketenangan, spiritualitas, keanggunan",
    "Periwinkle": "Ketenangan, spiritualitas, kreativitas, keanggunan",
    "Cornflower": "Kepercayaan, ketenangan, kreativitas, kebijaksanaan",
    "Steel": "Kekuatan, keandalan, efisiensi, modern",
    "Charcoal": "Kekuatan, elegan, misteri, keandalan",
    "Slate": "Kekuatan, keandalan, keseimbangan, kebijaksanaan",
    "Mist": "Ketenangan, kejernihan, kedamaian, kelembutan",
    "Frost": "Kesegaran, kesucian, kejernihan, awal baru",
    "Snow": "Kesucian, kesederhanaan, kedamaian, awal baru",
    "Cloud": "Ketenangan, kelembutan, kedamaian, kejernihan",
    "Fog": "Ketenangan, kelembutan, misteri, kedamaian",
    "Shadow": "Misteri, elegan, kekuatan, kedalaman",
    "Dusk": "Ketenangan, kelembutan, romantisme, kedamaian",
    "Twilight": "Misteri, romantisme, ketenangan, keindahan",
    "Dawn": "Awal baru, harapan, optimisme, kesegaran",
    "Sunset": "Kehangatan, gairah, keindahan, kreativitas",
    "Fire": "Gairah, energi, keberanian, kekuatan",
    "Flame": "Gairah, energi, semangat, kreativitas",
    "Scarlet": "Gairah, keberanian, kekuatan, kegembiraan",
    "Crimson": "Gairah, keberanian, kekuatan, kemewahan",
    "Cardinal": "Keberanian, gairah, kekuatan, keanggunan",
    "Berry": "Kekuatan, gairah, kemewahan, keanggunan",
    "Cherry": "Kegembiraan, gairah, kehangatan, kemewahan",
    "Raspberry": "Gairah, kehangatan, kemewahan, kegembiraan",
    "Strawberry": "Kegembiraan, gairah, kehangatan, optimisme",
    "Watermelon": "Kesegaran, kegembiraan, kehangatan, optimisme",
    "Mint": "Kesegaran, kedamaian, kesehatan, kebersihan",
    "Sage": "Kebijaksanaan, kedamaian, keseimbangan, alam",
    "Forest": "Alam, kedamaian, pertumbuhan, ketahanan",
    "Emerald": "Kemakmuran, pertumbuhan, keseimbangan, harmoni",
    "Jungle": "Alam, kedamaian, pertumbuhan, kekuatan",
    "Moss": "Alam, kedamaian, keseimbangan, kesederhanaan",
    "Fern": "Alam, kesegaran, pertumbuhan, kedamaian",
    "Pine": "Alam, ketahanan, kedamaian, keseimbangan",
}

COLOR_LIST = {
    "Merah": "#FF0000", "Hijau": "#00FF00", "Biru": "#0000FF",
    "Kuning": "#FFFF00", "Cyan": "#00FFFF", "Magenta": "#FF00FF",
    "Putih": "#FFFFFF", "Hitam": "#000000", "Abu-abu": "#808080",
    "Oranye": "#FFA500", "Pink": "#FFC0CB", "Ungu": "#800080",
    "Coklat": "#A52A2A", "Navy": "#000080", "Teal": "#008080",
    "Olive": "#808000", "Maroon": "#800000", "Silver": "#C0C0C0",
    "Lime": "#00FF00", "Aqua": "#00FFFF", "Fuchsia": "#FF00FF",
    "Biru Muda": "#ADD8E6", "Hijau Muda": "#90EE90", "Krem": "#FFFDD0",
    "Salem": "#FA8072", "Toska": "#40E0D0", "Lavender": "#E6E6FA",
    "Emas": "#FFD700", "Coral": "#FF7F50", "Indigo": "#4B0082",
    "Salmon": "#FA8072", "Tomat": "#FF6347", "Ruby": "#E0115F",
    "Sapphire": "#0F52BA", "Amber": "#FFBF00", "Jade": "#00A86B",
    "Turquoise": "#40E0D0", "Perak": "#C0C0C0", "Platinum": "#E5E4E2",
    "Rose": "#FF007F", "Apricot": "#FBCEB1", "Peach": "#FFDAB9",
    "Cinnamon": "#D2691E", "Chocolate": "#7B3F00", "Coffee": "#6F4E37",
    "Tan": "#D2B48C", "Beige": "#F5F5DC", "Ivory": "#FFFFF0",
    "Bone": "#E3DAC9", "Wheat": "#F5DEB3", "Moccasin": "#FFE4B5",
    "Navajo": "#FFDEAD", "Cornsilk": "#FFF8DC", "Blonde": "#FAF0BE",
    "Honey": "#E2B13C", "Gold": "#FFD700", "Bronze": "#CD7F32",
    "Copper": "#B87333", "Rust": "#B7410E", "Terra Cotta": "#E2725B",
    "Sienna": "#A0522D", "Umber": "#635147", "Burgundy": "#800020",
    "Wine": "#722F37", "Mauve": "#E0B0FF", "Orchid": "#DA70D6",
    "Plum": "#8E4585", "Violet": "#8A2BE2", "Lilac": "#C8A2C8",
    "Periwinkle": "#CCCCFF", "Cornflower": "#6495ED", "Steel": "#4682B4",
    "Charcoal": "#36454F", "Slate": "#708090", "Mist": "#E0E0E0",
    "Frost": "#F0F8FF", "Snow": "#FFFAFA", "Cloud": "#E0E0E0",
    "Fog": "#D3D3D3", "Shadow": "#8B8682", "Dusk": "#8B7D6B",
    "Twilight": "#4A4A4A", "Dawn": "#F5E6CA", "Sunset": "#FAD6A5",
    "Fire": "#E25822", "Flame": "#E25822", "Scarlet": "#FF2400",
    "Crimson": "#DC143C", "Cardinal": "#C41E3A", "Berry": "#8A2B34",
    "Cherry": "#DE3163", "Raspberry": "#E30B5C", "Strawberry": "#FC5A8D",
    "Watermelon": "#FF6B6B", "Mint": "#98FF98", "Sage": "#8A9A5B",
    "Forest": "#228B22", "Emerald": "#50C878", "Jungle": "#29AB87",
    "Moss": "#8A9A5B", "Fern": "#4F7942", "Pine": "#014540"
}

# ======================== FUNGSI KONVERSI =========================
def rgb_to_cmyk(r, g, b):
    r_prime = r / 255.0
    g_prime = g / 255.0
    b_prime = b / 255.0
    k = 1 - max(r_prime, g_prime, b_prime)
    if k == 1:
        return 0, 0, 0, 100
    c = (1 - r_prime - k) / (1 - k) * 100
    m = (1 - g_prime - k) / (1 - k) * 100
    y = (1 - b_prime - k) / (1 - k) * 100
    return round(c,1), round(m,1), round(y,1), round(k*100,1)

def cmyk_to_rgb(c, m, y, k):
    c /= 100.0; m /= 100.0; y /= 100.0; k /= 100.0
    r = 255 * (1 - c) * (1 - k)
    g = 255 * (1 - m) * (1 - k)
    b = 255 * (1 - y) * (1 - k)
    return round(r), round(g), round(b)

def rgb_to_hsv(r, g, b):
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0
    cmax = max(r_norm, g_norm, b_norm)
    cmin = min(r_norm, g_norm, b_norm)
    diff = cmax - cmin
    if diff == 0:
        h = 0
    elif cmax == r_norm:
        h = (60 * ((g_norm - b_norm) / diff) + 360) % 360
    elif cmax == g_norm:
        h = (60 * ((b_norm - r_norm) / diff) + 120) % 360
    elif cmax == b_norm:
        h = (60 * ((r_norm - g_norm) / diff) + 240) % 360
    s = 0 if cmax == 0 else (diff / cmax) * 100
    v = cmax * 100
    return round(h), round(s), round(v)

def hsv_to_rgb(h, s, v):
    s /= 100.0
    v /= 100.0
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    if h < 60:
        rp, gp, bp = c, x, 0
    elif h < 120:
        rp, gp, bp = x, c, 0
    elif h < 180:
        rp, gp, bp = 0, c, x
    elif h < 240:
        rp, gp, bp = 0, x, c
    elif h < 300:
        rp, gp, bp = x, 0, c
    else:
        rp, gp, bp = c, 0, x
    r = (rp + m) * 255
    g = (gp + m) * 255
    b = (bp + m) * 255
    return round(r), round(g), round(b)


def build_hue_sat_texture(cols, rows, value=100):
    """Buat SATU texture gradasi hue(x)/saturation(y) berukuran cols x
    rows pada value tertentu. Dipakai oleh ColorSquare & ColorSquareMini
    supaya kotak pemilih warna cukup 1 objek canvas (bukan cols*rows
    Rectangle terpisah yang berat dihitung ulang).

    Pakai format RGBA (4 byte/piksel), BUKAN RGB (3 byte/piksel) --
    beberapa GPU Android tidak menangani alignment baris RGB dengan
    benar dan hasilnya bisa tampil hitam total. RGBA selalu rata
    (aligned) di 4 byte sehingga aman di semua perangkat.
    """
    buf = bytearray(cols * rows * 4)
    for j in range(rows):
        sat = (j / rows) * 100
        row_off = j * cols * 4
        for i in range(cols):
            hue = (i / cols) * 360
            r, g, b = hsv_to_rgb(hue, sat, value)
            idx = row_off + i * 4
            buf[idx] = r
            buf[idx + 1] = g
            buf[idx + 2] = b
            buf[idx + 3] = 255
    texture = Texture.create(size=(cols, rows), colorfmt='rgba')
    texture.mag_filter = 'nearest'
    texture.min_filter = 'nearest'
    texture.blit_buffer(bytes(buf), colorfmt='rgba', bufferfmt='ubyte')
    return texture

def rgb_to_hsl(r, g, b):
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0
    cmax = max(r_norm, g_norm, b_norm)
    cmin = min(r_norm, g_norm, b_norm)
    diff = cmax - cmin
    l = (cmax + cmin) / 2
    if diff == 0:
        h = 0
        s = 0
    else:
        if l < 0.5:
            s = diff / (cmax + cmin)
        else:
            s = diff / (2 - cmax - cmin)
        if cmax == r_norm:
            h = (60 * ((g_norm - b_norm) / diff) + 360) % 360
        elif cmax == g_norm:
            h = (60 * ((b_norm - r_norm) / diff) + 120) % 360
        elif cmax == b_norm:
            h = (60 * ((r_norm - g_norm) / diff) + 240) % 360
    return round(h), round(s*100), round(l*100)

def hsl_to_rgb(h, s, l):
    s /= 100.0
    l /= 100.0
    c = (1 - abs(2*l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c/2
    if h < 60:
        rp, gp, bp = c, x, 0
    elif h < 120:
        rp, gp, bp = x, c, 0
    elif h < 180:
        rp, gp, bp = 0, c, x
    elif h < 240:
        rp, gp, bp = 0, x, c
    elif h < 300:
        rp, gp, bp = x, 0, c
    else:
        rp, gp, bp = c, 0, x
    r = (rp + m) * 255
    g = (gp + m) * 255
    b = (bp + m) * 255
    return round(r), round(g), round(b)

def rgb_to_lab(r, g, b):
    r_n = r / 255.0
    g_n = g / 255.0
    b_n = b / 255.0
    def gamma_correct(c):
        if c <= 0.04045:
            return c / 12.92
        else:
            return ((c + 0.055) / 1.055) ** 2.4
    r_lin = gamma_correct(r_n)
    g_lin = gamma_correct(g_n)
    b_lin = gamma_correct(b_n)
    x = r_lin * 0.4124564 + g_lin * 0.3575761 + b_lin * 0.1804375
    y = r_lin * 0.2126729 + g_lin * 0.7151522 + b_lin * 0.0721750
    z = r_lin * 0.0193339 + g_lin * 0.1191920 + b_lin * 0.9503041
    xn, yn, zn = 0.95047, 1.00000, 0.82584
    x /= xn
    y /= yn
    z /= zn
    def f(t):
        if t > 0.008856:
            return t ** (1/3)
        else:
            return (7.787 * t) + (16/116)
    fx = f(x)
    fy = f(y)
    fz = f(z)
    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b_lab = 200 * (fy - fz)
    return round(L, 2), round(a, 2), round(b_lab, 2)

def lab_to_rgb(L, a, b_lab):
    xn, yn, zn = 0.95047, 1.00000, 0.82584
    def f_inv(t):
        if t > 0.206893:
            return t ** 3
        else:
            return (t - 16/116) / 7.787
    fy = (L + 16) / 116
    fx = fy + (a / 500)
    fz = fy - (b_lab / 200)
    x = f_inv(fx) * xn
    y = f_inv(fy) * yn
    z = f_inv(fz) * zn
    r_lin = x *  3.2404542 + y * -1.5371385 + z * -0.4985314
    g_lin = x * -0.9692660 + y *  1.8760108 + z *  0.0415560
    b_lin = x *  0.0556434 + y * -0.2040259 + z *  1.0572252
    def gamma_inv(c):
        if c <= 0.0031308:
            return 12.92 * c
        else:
            return 1.055 * (c ** (1/2.4)) - 0.055
    r = gamma_inv(r_lin)
    g = gamma_inv(g_lin)
    b = gamma_inv(b_lin)
    r = max(0, min(1, r)) * 255
    g = max(0, min(1, g)) * 255
    b = max(0, min(1, b)) * 255
    return round(r), round(g), round(b)

def find_nearest_color_name(hex_color):
    target = get_color_from_hex(hex_color)
    min_dist = float('inf')
    nearest = "Tidak diketahui"
    for name, h in COLOR_LIST.items():
        color = get_color_from_hex(h)
        dist = math.sqrt((target[0]-color[0])**2 + (target[1]-color[1])**2 + (target[2]-color[2])**2)
        if dist < min_dist:
            min_dist = dist
            nearest = name
    return nearest

def get_color_meaning(name):
    return COLOR_MEANINGS.get(name, "Arti tidak tersedia")

# ======================== FUNGSI DETEKSI DOMINAN =========================
def get_dominant_colors(image_texture, num_colors=20, sample_size=3000):
    if not image_texture:
        return []
    try:
        pixels = image_texture.pixels
        width, height = image_texture.size
        if not pixels:
            return []
        step = 4 if len(pixels) == width * height * 4 else 3
        total_pixels = width * height
        sample_indices = random.sample(range(total_pixels), min(sample_size, total_pixels))
        pixel_list = []
        for idx in sample_indices:
            pos = idx * step
            r = pixels[pos]
            g = pixels[pos+1]
            b = pixels[pos+2]
            pixel_list.append((r, g, b))
        if not pixel_list:
            return []
        hsv_list = [rgb_to_hsv(r, g, b) for (r,g,b) in pixel_list]
        num_bins = 72
        bin_size = 360 / num_bins
        bins = [0] * num_bins
        bin_hsv = [{'h':0, 's':0, 'v':0, 'count':0} for _ in range(num_bins)]
        for h, s, v in hsv_list:
            bin_idx = int(h // bin_size) % num_bins
            bins[bin_idx] += 1
            bin_hsv[bin_idx]['h'] += h
            bin_hsv[bin_idx]['s'] += s
            bin_hsv[bin_idx]['v'] += v
            bin_hsv[bin_idx]['count'] += 1
        top_bins = sorted(range(num_bins), key=lambda i: bins[i], reverse=True)[:num_colors]
        dominant = []
        for bin_idx in top_bins:
            count = bin_hsv[bin_idx]['count']
            if count == 0:
                continue
            avg_h = bin_hsv[bin_idx]['h'] / count
            avg_s = bin_hsv[bin_idx]['s'] / count
            avg_v = bin_hsv[bin_idx]['v'] / count
            r, g, b = hsv_to_rgb(int(avg_h), int(avg_s), int(avg_v))
            dominant.append((r, g, b))
        return dominant
    except Exception as e:
        print("Error in get_dominant_colors:", e)
        return []

def generate_color_advice(colors):
    if not colors:
        return "Tidak ada warna yang terdeteksi."
    n = len(colors)
    warm_count = 0
    cool_count = 0
    neutral_count = 0
    avg_saturation = 0
    avg_value = 0
    for (r,g,b) in colors:
        h, s, v = rgb_to_hsv(r, g, b)
        avg_saturation += s
        avg_value += v
        if 15 <= h < 45 or 45 <= h < 75 or h >= 345 or h < 15:
            warm_count += 1
        elif 75 <= h < 165 or 165 <= h < 255 or 255 <= h < 345:
            cool_count += 1
        else:
            neutral_count += 1
    avg_saturation /= n
    avg_value /= n
    if warm_count > cool_count and warm_count > neutral_count:
        dominant_temp = "hangat"
    elif cool_count > warm_count and cool_count > neutral_count:
        dominant_temp = "dingin"
    else:
        dominant_temp = "netral"
    advices = []
    advices.append(f"🎨 Dari {n} warna dominan yang terdeteksi:")
    advices.append(f"   - Warna hangat: {warm_count} warna")
    advices.append(f"   - Warna dingin: {cool_count} warna")
    advices.append(f"   - Warna netral: {neutral_count} warna")
    advices.append(f"   - Dominasi: {dominant_temp.capitalize()}")
    if avg_saturation > 70:
        advices.append("🎯 Saturasi tinggi -> gaya ceria, pop art, branding kuat.")
    elif avg_saturation < 30:
        advices.append("🎯 Saturasi rendah -> gaya minimalis, elegan, monokrom.")
    else:
        advices.append("🎯 Saturasi sedang -> gaya seimbang dan natural.")
    if avg_value > 70:
        advices.append("☀️ Kecerahan tinggi -> tampilan cerah, segar, energik.")
    elif avg_value < 30:
        advices.append("🌙 Kecerahan rendah -> gaya dramatis, mewah, misterius.")
    else:
        advices.append("🌤️ Kecerahan sedang -> tampilan nyaman dan tenang.")
    if dominant_temp == "hangat":
        advices.append("🔥 Rekomendasi grading: tone hangat (kuning, oranye, merah) untuk kesan nyaman, vintage, atau tropis.")
    elif dominant_temp == "dingin":
        advices.append("❄️ Rekomendasi grading: tone dingin (biru, hijau, ungu) untuk kesan tenang, modern, atau profesional.")
    else:
        advices.append("⚖️ Rekomendasi grading: seimbangkan antara tone hangat dan dingin untuk harmoni.")
    if n >= 15:
        advices.append("📌 Palet warna sangat kaya, cocok untuk desain grafis, ilustrasi, atau branding yang kompleks.")
    elif n >= 8:
        advices.append("📌 Palet warna cukup beragam, cocok untuk desain minimalis atau aksen.")
    else:
        advices.append("📌 Palet sederhana, cocok untuk gaya monokrom atau fokus pada satu warna.")
    return "\n".join(advices)
    

# ======================== WIDGET WARNA =========================
class ColorSquare(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hue = 0
        self.saturation = 100
        self.value = 100
        self.cols = GridSettings.cols
        self.rows = GridSettings.rows
        self.gradient_instructions = []
        self.indicator_instructions = []
        self.bind(pos=self.on_pos_size, size=self.on_pos_size)
        Clock.schedule_once(self.on_pos_size, 0.1)
        GridSettings.register(self)

    def on_pos_size(self, *args):
        self.draw_gradient()

    def set_grid(self, cols, rows):
        self.cols = max(2, int(cols))
        self.rows = max(2, int(rows))
        self.draw_gradient()

    def draw_gradient(self):
        # 1 texture tunggal, bukan cols*rows Rectangle terpisah (berat).
        for instr in self.gradient_instructions:
            self.canvas.remove(instr)
        self.gradient_instructions.clear()
        x, y = self.pos
        w, h = self.size
        if w <= 0 or h <= 0:
            return
        texture = build_hue_sat_texture(self.cols, self.rows, value=100)
        with self.canvas:
            # Color(1,1,1,1) WAJIB ditegaskan di sini -- kalau tidak,
            # texture ini akan mewarisi warna Color() terakhir yang
            # masih "aktif" dari indikator titik (yang berakhir warna
            # HITAM), sehingga seluruh texture ikut tampil hitam.
            color_reset = Color(1, 1, 1, 1)
            self.gradient_instructions.append(color_reset)
            rect = Rectangle(pos=(x, y), size=(w, h), texture=texture)
            self.gradient_instructions.append(rect)
        self.draw_indicator()

    def draw_indicator(self):
        for instr in self.indicator_instructions:
            self.canvas.remove(instr)
        self.indicator_instructions.clear()
        x, y = self.pos
        w, h = self.size
        if w <= 0 or h <= 0:
            return
        px = x + (self.hue / 360) * w
        py = y + (self.saturation / 100) * h
        with self.canvas:
            Color(1, 1, 1, 1)
            ell = Ellipse(pos=(px-8, py-8), size=(16,16))
            self.indicator_instructions.append(ell)
            Color(0, 0, 0, 1)
            ell2 = Ellipse(pos=(px-8, py-8), size=(16,16), width=2)
            self.indicator_instructions.append(ell2)
            Color(0, 0, 0, 1)
            ell3 = Ellipse(pos=(px-2, py-2), size=(4,4))
            self.indicator_instructions.append(ell3)

    def set_hue_sat(self, hue, sat):
        self.hue = hue
        self.saturation = sat
        self.draw_indicator()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.update_from_touch(touch)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            self.update_from_touch(touch)
            return True
        return super().on_touch_move(touch)

    def update_from_touch(self, touch):
        x, y = touch.pos
        w, h = self.size
        if w <= 0 or h <= 0:
            return
        hue = ((x - self.x) / w) * 360
        sat = ((y - self.y) / h) * 100
        hue = max(0, min(360, hue))
        sat = max(0, min(100, sat))
        self.hue = round(hue)
        self.saturation = round(sat)
        self.draw_indicator()
        if hasattr(self, 'on_color_changed'):
            self.on_color_changed(self.hue, self.saturation, self.value)

class ValueBar(Widget):
    """Slider kecerahan (Value) bergaya gambar referensi: batang gradasi
    warna (mengikuti hue/saturation aktif) dengan gagang bulat, tanpa
    label teks/angka di sampingnya.

    PENTING (perbaikan performa): batang gradasi digambar sebagai SATU
    texture halus (bukan puluhan potongan RoundedRectangle), dan hanya
    dibuat ulang saat hue/saturation ATAU ukuran widget berubah -- BUKAN
    setiap kali jari digeser. Saat digeser, yang digambar ulang cuma
    gagangnya (3 bentuk kecil), makanya jadi mulus/tidak patah-patah.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hue = 0
        self.saturation = 100
        self.value = 100
        self._track_instructions = []
        self._handle_instructions = []
        self.bind(pos=self._redraw_track, size=self._redraw_track)
        Clock.schedule_once(self._redraw_track, 0.1)

    def set_hue_sat(self, hue, saturation):
        self.hue = hue
        self.saturation = saturation
        self._redraw_track()

    def _make_gradient_texture(self, width_px):
        # Format RGBA (bukan RGB) -- lebih universal aman di semua GPU
        # Android, hindari masalah alignment baris yang bisa bikin
        # texture tampil hitam total di sebagian perangkat.
        width_px = max(2, int(width_px))
        buf = bytearray(width_px * 4)
        for i in range(width_px):
            v = (i / (width_px - 1)) * 100
            r, g, b = hsv_to_rgb(self.hue, self.saturation, v)
            buf[i*4:i*4+4] = bytes((r, g, b, 255))
        tex = Texture.create(size=(width_px, 1), colorfmt='rgba')
        tex.mag_filter = 'linear'
        tex.min_filter = 'linear'
        tex.blit_buffer(bytes(buf), colorfmt='rgba', bufferfmt='ubyte')
        return tex

    def _redraw_track(self, *_args):
        for instr in self._track_instructions:
            self.canvas.remove(instr)
        self._track_instructions.clear()
        x, y = self.pos
        w, h = self.size
        if w <= 0 or h <= 0:
            return
        texture = self._make_gradient_texture(w)
        with self.canvas:
            # Tegaskan putih dulu -- supaya texture tidak mewarisi warna
            # ungu/hitam sisa dari gambar gagang sebelumnya.
            color_reset = Color(1, 1, 1, 1)
            self._track_instructions.append(color_reset)
            track = RoundedRectangle(pos=(x, y + h*0.32), size=(w, h*0.36),
                                      radius=[h*0.18], texture=texture)
            self._track_instructions.append(track)
        self._redraw_handle()

    def _redraw_handle(self, *_args):
        for instr in self._handle_instructions:
            self.canvas.remove(instr)
        self._handle_instructions.clear()
        x, y = self.pos
        w, h = self.size
        if w <= 0 or h <= 0:
            return
        hx = x + (self.value / 100.0) * w
        hy = y + h / 2.0
        handle_r = h * 0.42
        with self.canvas:
            Color(1, 1, 1, 1)
            handle_bg = Ellipse(pos=(hx - handle_r, hy - handle_r), size=(handle_r*2, handle_r*2))
            self._handle_instructions.append(handle_bg)
            Color(*ACCENT_PURPLE)
            ring = Line(circle=(hx, hy, handle_r * 0.72), width=dp(2))
            self._handle_instructions.append(ring)
            dot = Ellipse(pos=(hx - handle_r*0.32, hy - handle_r*0.32), size=(handle_r*0.64, handle_r*0.64))
            self._handle_instructions.append(dot)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._update_from_touch(touch)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            self._update_from_touch(touch)
            return True
        return super().on_touch_move(touch)

    def _update_from_touch(self, touch):
        w = self.width
        if w <= 0:
            return
        val = ((touch.x - self.x) / w) * 100
        val = max(0, min(100, round(val)))
        self.value = val
        self._redraw_handle()
        if hasattr(self, 'on_value_changed'):
            self.on_value_changed(val)


class ColorSquareMini(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hue = 0
        self.saturation = 100
        self.value = 100
        self.cols = GridSettings.cols
        self.rows = GridSettings.rows
        self.gradient_instructions = []
        self.indicator_instructions = []
        self.extra_hue = None
        self.extra_saturation = None
        self.bind(pos=self.on_pos_size, size=self.on_pos_size)
        Clock.schedule_once(self.on_pos_size, 0.1)
        GridSettings.register(self)

    def on_pos_size(self, *args):
        self.draw_gradient()

    def set_grid(self, cols, rows):
        self.cols = max(2, int(cols))
        self.rows = max(2, int(rows))
        self.draw_gradient()

    def draw_gradient(self):
        # 1 texture tunggal, bukan cols*rows Rectangle terpisah (berat).
        for instr in self.gradient_instructions:
            self.canvas.remove(instr)
        self.gradient_instructions.clear()
        x, y = self.pos
        w, h = self.size
        if w <= 0 or h <= 0:
            return
        texture = build_hue_sat_texture(self.cols, self.rows, value=100)
        with self.canvas:
            # Color(1,1,1,1) WAJIB ditegaskan di sini -- kalau tidak,
            # texture ini akan mewarisi warna Color() terakhir yang
            # masih "aktif" dari indikator titik (yang berakhir warna
            # HITAM), sehingga seluruh texture ikut tampil hitam.
            color_reset = Color(1, 1, 1, 1)
            self.gradient_instructions.append(color_reset)
            rect = Rectangle(pos=(x, y), size=(w, h), texture=texture)
            self.gradient_instructions.append(rect)
        self.draw_indicator()

    def draw_indicator(self):
        for instr in self.indicator_instructions:
            self.canvas.remove(instr)
        self.indicator_instructions.clear()
        x, y = self.pos
        w, h = self.size
        if w <= 0 or h <= 0:
            return
        px = x + (self.hue / 360) * w
        py = y + (self.saturation / 100) * h
        with self.canvas:
            Color(1, 1, 1, 1)
            ell = Ellipse(pos=(px-6, py-6), size=(12, 12))
            self.indicator_instructions.append(ell)
            Color(0, 0, 0, 1)
            ell2 = Ellipse(pos=(px-6, py-6), size=(12, 12), width=2)
            self.indicator_instructions.append(ell2)
            Color(0, 0, 0, 1)
            ell3 = Ellipse(pos=(px-2, py-2), size=(4, 4))
            self.indicator_instructions.append(ell3)

    def set_hue_sat(self, hue, sat):
        self.hue = hue
        self.saturation = sat
        self.draw_indicator()

    def set_extra_point(self, hue, sat):
        self.extra_hue = hue
        self.extra_saturation = sat
        self.draw_indicator()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.update_from_touch(touch)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            self.update_from_touch(touch)
            return True
        return super().on_touch_move(touch)

    def update_from_touch(self, touch):
        x, y = touch.pos
        w, h = self.size
        if w <= 0 or h <= 0:
            return
        hue = ((x - self.x) / w) * 360
        sat = ((y - self.y) / h) * 100
        hue = max(0, min(360, hue))
        sat = max(0, min(100, sat))
        self.hue = round(hue)
        self.saturation = round(sat)
        self.draw_indicator()
        if hasattr(self, 'on_color_changed'):
            self.on_color_changed(self.hue, self.saturation, self.value)

class GradientRamp(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.r1, self.g1, self.b1 = 255, 0, 0
        self.r2, self.g2, self.b2 = 0, 0, 255
        self.bind(pos=self.redraw, size=self.redraw)
        Clock.schedule_once(self.redraw, 0.1)

    def set_colors(self, r1, g1, b1, r2, g2, b2):
        self.r1, self.g1, self.b1 = r1, g1, b1
        self.r2, self.g2, self.b2 = r2, g2, b2
        self.redraw()

    def redraw(self, *args):
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size
        if w <= 0 or h <= 0:
            return
        steps = 400
        step_w = w / steps
        with self.canvas:
            for i in range(steps):
                t = i / steps
                r = int(self.r1 + (self.r2 - self.r1) * t)
                g = int(self.g1 + (self.g2 - self.g1) * t)
                b = int(self.b1 + (self.b2 - self.b1) * t)
                Color(r/255.0, g/255.0, b/255.0, 1)
                Rectangle(pos=(x + i*step_w, y), size=(step_w+1, h))

# ==================== Komponen UI flat bergaya referensi ====================
ACCENT_PURPLE = get_color_from_hex('#5A31D6')
CARD_BG = (0.96, 0.96, 0.97, 1)


class FlatButton(ButtonBehavior, Label):
    """Tombol datar bersudut bulat (pengganti Button bawaan Kivy yang kotak/abu2),
    dipakai untuk Hex/Nama/Arti, Ubah, Buat Gradasi, dsb -- gaya seperti referensi."""
    def __init__(self, bg_rgba=(1, 1, 1, 1), border_rgba=(0.8, 0.8, 0.85, 1),
                 radius=None, **kwargs):
        kwargs.setdefault('halign', 'center')
        kwargs.setdefault('valign', 'middle')
        super().__init__(**kwargs)
        self.bind(size=lambda *_a: setattr(self, 'text_size', self.size))
        self.bg_rgba = bg_rgba
        self.border_rgba = border_rgba
        self.radius = [radius if radius is not None else dp(10)]
        with self.canvas.before:
            self._border_color = Color(*self.border_rgba)
            self._border_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=self.radius)
            self._bg_color = Color(*self.bg_rgba)
            self._bg_rect = RoundedRectangle(
                pos=(self.x + dp(1.5), self.y + dp(1.5)),
                size=(self.width - dp(3), self.height - dp(3)),
                radius=self.radius)
        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, *_args):
        self._border_rect.pos = self.pos
        self._border_rect.size = self.size
        self._bg_rect.pos = (self.x + dp(1.5), self.y + dp(1.5))
        self._bg_rect.size = (self.width - dp(3), self.height - dp(3))


def add_rounded_card(widget, bg_rgba=CARD_BG, radius=dp(14)):
    """Tempel latar kartu bulat putih/abu2 muda di belakang sebuah widget,
    mirip kartu-kartu di gambar referensi (info warna, RGB, grid, gradasi)."""
    with widget.canvas.before:
        Color(*bg_rgba)
        rect = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius])

    def _update(*_args):
        rect.pos = widget.pos
        rect.size = widget.size

    widget.bind(pos=_update, size=_update)
    return rect


def flat_textinput(**kwargs):
    """Kotak angka putih dengan sudut membulat & garis tepi abu tipis,
    angka besar rata tengah -- sesuai desain referensi (Nilai Warna, Grid)."""
    kwargs.setdefault('background_color', (1, 1, 1, 1))
    kwargs.setdefault('foreground_color', (0.05, 0.05, 0.05, 1))
    kwargs.setdefault('cursor_color', ACCENT_PURPLE)
    kwargs.setdefault('halign', 'center')
    kwargs.setdefault('padding', [dp(6), dp(14), dp(6), dp(14)])
    inp = TextInput(**kwargs)
    inp.background_normal = ''
    inp.background_active = ''
    inp.background_disabled_normal = ''

    radius = dp(10)
    with inp.canvas.after:
        Color(0.78, 0.78, 0.82, 1)
        border = Line(rounded_rectangle=(inp.x, inp.y, inp.width, inp.height, radius), width=dp(1.3))

    def _sync_border(*_args):
        border.rounded_rectangle = (inp.x, inp.y, inp.width, inp.height, radius)

    inp.bind(pos=_sync_border, size=_sync_border)
    return inp


class ColorFormatPanel(BoxLayout):
    def __init__(self, **kwargs):
        # PENTING: jangan set self.size_hint di sini -- kalau di-set, itu akan
        # MENIMPA size_hint/height yang dikirim MainContent lewat kwargs
        # (size_hint=(1, None), height=dp(150)), menyebabkan tinggi panel ini
        # jadi tidak terhitung benar dan tumpang-tindih dengan baris di
        # bawahnya (bug yang bikin kotak Nilai Warna hilang/numpuk & aplikasi
        # jadi berat karena layout dihitung ulang terus).
        kwargs.setdefault('size_hint', (1, None))
        kwargs.setdefault('height', dp(150))
        super().__init__(orientation='vertical', spacing=5, **kwargs)
        self._updating = False

        # Spinner format dibuat TAPI tidak ditaruh sebagai baris besar di sini
        # (referensi tidak punya baris "Format Warna : RGB" yang mencolok).
        # Spinner format dibuat dengan ukuran TETAP sejak awal (size_hint None,
        # None + width/height eksplisit) supaya tidak melar/menabrak baris lain
        # ketika ditempel ke parent manapun (referensi tidak punya kotak
        # "Format Warna: RGB" besar -- ini dibuat sekecil & aman mungkin).
        self.format_spinner = Spinner(
            text="RGB",
            values=("RGB", "CMYK", "LAB", "HSV", "HSL", "HEX"),
            font_size=20,
            size_hint=(None, None),
            size=(dp(92), dp(36)),
            background_normal='',
            background_down='',
            background_color=(0.90, 0.90, 0.93, 1),
            color=(0.15, 0.15, 0.15, 1),
        )
        self.format_spinner.bind(text=self.on_format_change)

        self.input_container = BoxLayout(size_hint=(1, 1), spacing=5)
        self.add_widget(self.input_container)

        self.format_widgets = {}
        self.inputs = {}

        # RGB
        rgb_box = BoxLayout(spacing=dp(14))
        self.inputs["RGB"] = []
        for label in ("R", "G", "B"):
            box = BoxLayout(orientation='vertical', size_hint_x=1/3)
            box.add_widget(Label(text=label, font_size=39, color=(0,0,0,1), size_hint_y=0.3))
            inp = flat_textinput(text="255", input_filter='int', multiline=False, font_size=43)
            inp.bind(text=self.on_input_change)
            box.add_widget(inp)
            rgb_box.add_widget(box)
            self.inputs["RGB"].append(inp)
        self.format_widgets["RGB"] = rgb_box

        # CMYK
        cmyk_box = BoxLayout(spacing=dp(14))
        self.inputs["CMYK"] = []
        for label in ("C", "M", "Y", "K"):
            box = BoxLayout(orientation='vertical', size_hint_x=1/4)
            box.add_widget(Label(text=label, font_size=39, color=(0,0,0,1), size_hint_y=0.3))
            inp = flat_textinput(text="0", input_filter='float', multiline=False, font_size=43)
            inp.bind(text=self.on_input_change)
            box.add_widget(inp)
            cmyk_box.add_widget(box)
            self.inputs["CMYK"].append(inp)
        self.format_widgets["CMYK"] = cmyk_box

        # LAB
        lab_box = BoxLayout(spacing=dp(14))
        self.inputs["LAB"] = []
        for label in ("L", "A", "B"):
            box = BoxLayout(orientation='vertical', size_hint_x=1/3)
            box.add_widget(Label(text=label, font_size=39, color=(0,0,0,1), size_hint_y=0.3))
            inp = flat_textinput(text="100", input_filter='float', multiline=False, font_size=43)
            inp.bind(text=self.on_input_change)
            box.add_widget(inp)
            lab_box.add_widget(box)
            self.inputs["LAB"].append(inp)
        self.format_widgets["LAB"] = lab_box

        # HSV
        hsv_box = BoxLayout(spacing=dp(14))
        self.inputs["HSV"] = []
        for label in ("H", "S", "V"):
            box = BoxLayout(orientation='vertical', size_hint_x=1/3)
            box.add_widget(Label(text=label, font_size=39, color=(0,0,0,1), size_hint_y=0.3))
            inp = flat_textinput(text="0", input_filter='float', multiline=False, font_size=43)
            inp.bind(text=self.on_input_change)
            box.add_widget(inp)
            hsv_box.add_widget(box)
            self.inputs["HSV"].append(inp)
        self.format_widgets["HSV"] = hsv_box

        # HSL
        hsl_box = BoxLayout(spacing=dp(14))
        self.inputs["HSL"] = []
        for label in ("H", "S", "L"):
            box = BoxLayout(orientation='vertical', size_hint_x=1/3)
            box.add_widget(Label(text=label, font_size=39, color=(0,0,0,1), size_hint_y=0.3))
            inp = flat_textinput(text="0", input_filter='float', multiline=False, font_size=43)
            inp.bind(text=self.on_input_change)
            box.add_widget(inp)
            hsl_box.add_widget(box)
            self.inputs["HSL"].append(inp)
        self.format_widgets["HSL"] = hsl_box

        # HEX
        hex_box = BoxLayout(spacing=dp(14))
        self.inputs["HEX"] = []
        box = BoxLayout(orientation='vertical', size_hint_x=1)
        box.add_widget(Label(text="HEX", font_size=39, color=(0,0,0,1), size_hint_y=0.3))
        inp = flat_textinput(text="#FF0000", multiline=False, font_size=43)
        inp.bind(text=self.on_input_change)
        box.add_widget(inp)
        hex_box.add_widget(box)
        self.inputs["HEX"].append(inp)
        self.format_widgets["HEX"] = hex_box

        self.input_container.add_widget(self.format_widgets["RGB"])

    def on_format_change(self, spinner, text):
        self.input_container.clear_widgets()
        self.input_container.add_widget(self.format_widgets[text])

    def on_input_change(self, instance, value):
        if self._updating:
            return
        fmt = self.format_spinner.text
        try:
            if fmt == "RGB":
                r = int(self.inputs["RGB"][0].text) if self.inputs["RGB"][0].text else 0
                g = int(self.inputs["RGB"][1].text) if self.inputs["RGB"][1].text else 0
                b = int(self.inputs["RGB"][2].text) if self.inputs["RGB"][2].text else 0
                r = max(0, min(255, r)); g = max(0, min(255, g)); b = max(0, min(255, b))
                if hasattr(self, 'on_color_update'):
                    self.on_color_update(r, g, b)
                return
            elif fmt == "CMYK":
                c = float(self.inputs["CMYK"][0].text) if self.inputs["CMYK"][0].text else 0
                m = float(self.inputs["CMYK"][1].text) if self.inputs["CMYK"][1].text else 0
                y = float(self.inputs["CMYK"][2].text) if self.inputs["CMYK"][2].text else 0
                k = float(self.inputs["CMYK"][3].text) if self.inputs["CMYK"][3].text else 0
                c = max(0, min(100, c)); m = max(0, min(100, m)); y = max(0, min(100, y)); k = max(0, min(100, k))
                r, g, b = cmyk_to_rgb(c, m, y, k)
                if hasattr(self, 'on_color_update'):
                    self.on_color_update(r, g, b)
                return
            elif fmt == "LAB":
                L = float(self.inputs["LAB"][0].text) if self.inputs["LAB"][0].text else 0
                a = float(self.inputs["LAB"][1].text) if self.inputs["LAB"][1].text else 0
                b_lab = float(self.inputs["LAB"][2].text) if self.inputs["LAB"][2].text else 0
                L = max(0, min(100, L)); a = max(-128, min(127, a)); b_lab = max(-128, min(127, b_lab))
                r, g, b = lab_to_rgb(L, a, b_lab)
                if hasattr(self, 'on_color_update'):
                    self.on_color_update(r, g, b)
                return
            elif fmt == "HSV":
                h = float(self.inputs["HSV"][0].text) if self.inputs["HSV"][0].text else 0
                s = float(self.inputs["HSV"][1].text) if self.inputs["HSV"][1].text else 0
                v = float(self.inputs["HSV"][2].text) if self.inputs["HSV"][2].text else 0
                h = max(0, min(360, h)); s = max(0, min(100, s)); v = max(0, min(100, v))
                r, g, b = hsv_to_rgb(h, s, v)
                if hasattr(self, 'on_color_update'):
                    self.on_color_update(r, g, b)
                return
            elif fmt == "HSL":
                h = float(self.inputs["HSL"][0].text) if self.inputs["HSL"][0].text else 0
                s = float(self.inputs["HSL"][1].text) if self.inputs["HSL"][1].text else 0
                l = float(self.inputs["HSL"][2].text) if self.inputs["HSL"][2].text else 0
                h = max(0, min(360, h)); s = max(0, min(100, s)); l = max(0, min(100, l))
                r, g, b = hsl_to_rgb(h, s, l)
                if hasattr(self, 'on_color_update'):
                    self.on_color_update(r, g, b)
                return
            elif fmt == "HEX":
                hex_str = self.inputs["HEX"][0].text.strip()
                if len(hex_str) == 7 and hex_str[0] == '#':
                    r = int(hex_str[1:3], 16)
                    g = int(hex_str[3:5], 16)
                    b = int(hex_str[5:7], 16)
                    if hasattr(self, 'on_color_update'):
                        self.on_color_update(r, g, b)
                return
        except ValueError:
            pass

    def update_values(self, r, g, b):
        self._updating = True
        self.inputs["RGB"][0].text = str(r)
        self.inputs["RGB"][1].text = str(g)
        self.inputs["RGB"][2].text = str(b)
        c, m, y, k = rgb_to_cmyk(r, g, b)
        self.inputs["CMYK"][0].text = str(c)
        self.inputs["CMYK"][1].text = str(m)
        self.inputs["CMYK"][2].text = str(y)
        self.inputs["CMYK"][3].text = str(k)
        L, a_lab, b_lab = rgb_to_lab(r, g, b)
        self.inputs["LAB"][0].text = str(L)
        self.inputs["LAB"][1].text = str(a_lab)
        self.inputs["LAB"][2].text = str(b_lab)
        h, s, v = rgb_to_hsv(r, g, b)
        self.inputs["HSV"][0].text = str(h)
        self.inputs["HSV"][1].text = str(s)
        self.inputs["HSV"][2].text = str(v)
        h_l, s_l, l_l = rgb_to_hsl(r, g, b)
        self.inputs["HSL"][0].text = str(h_l)
        self.inputs["HSL"][1].text = str(s_l)
        self.inputs["HSL"][2].text = str(l_l)
        hex_code = "#{:02X}{:02X}{:02X}".format(r, g, b)
        self.inputs["HEX"][0].text = hex_code
        self._updating = False

# ======================== Halaman 1: Color Picker =========================
class MainContent(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self._updating = False

        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        # Halaman ini di-scroll (bukan dipaksa muat 1 layar) supaya setiap
        # bagian bisa punya tinggi yang cukup tanpa tumpang-tindih.
        self.color_square = ColorSquare(size_hint=(1, None), height=dp(355))
        self.color_square.on_color_changed = self.square_changed
        self.add_widget(self.color_square)

        value_layout = BoxLayout(size_hint=(1, None), height=dp(46), padding=[dp(14), 0])
        self.value_slider = ValueBar(size_hint=(1, 1))
        self.value_slider.on_value_changed = self.on_value_change
        value_layout.add_widget(self.value_slider)
        self.add_widget(value_layout)
        self.value_layout = value_layout  # disimpan supaya bisa dipakai untuk Export Tampilan Penuh


        # Sisa kontrol (format warna, grid warna, info, tombol copy, gradasi)
        # ditaruh di area yang bisa di-scroll, supaya tidak berebut ruang
        # dan tidak tumpang-tindih di layar kecil. Kotak hue-saturation &
        # slider Value TIDAK dimasukkan ke sini karena butuh drag 2 arah
        # yang bisa konflik dengan gesture scroll vertikal.
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, bar_width=dp(6))
        content = BoxLayout(orientation='vertical', size_hint_y=None,
                             padding=dp(10), spacing=dp(10))
        content.bind(minimum_height=content.setter('height'))
        scroll.add_widget(content)
        self.add_widget(scroll)
        self.scroll_content = content  # disimpan supaya bisa dipakai untuk Export Tampilan Penuh
        self.tab_strip_widget = None  # diisi dari luar (ColorFinderApp.build) setelah TabbedPanel jadi

        # ==== Urutan konten mengikuti referensi (gambar 1): ====
        # kartu info warna (preview+nama+hex) -> arti warna -> tombol
        # Hex/Nama/Arti -> Nilai Warna (RGB dkk) -> Grid -> Gradasi -> Export

        # ---- Kartu info warna: preview besar + nama + hex ----
        info_box = BoxLayout(size_hint=(1, None), height=dp(170), spacing=dp(14), padding=dp(12))
        add_rounded_card(info_box)
        self.color_preview = BoxLayout(size_hint=(0.3, 1))
        with self.color_preview.canvas:
            self.preview_color = Color(1, 0, 0, 1)
            self.preview_rect = RoundedRectangle(pos=self.color_preview.pos, size=self.color_preview.size, radius=[dp(14)])
        self.color_preview.bind(pos=self.update_rect, size=self.update_rect)
        info_box.add_widget(self.color_preview)

        text_box = BoxLayout(orientation='vertical', size_hint=(0.7, 1))
        self.name_label = Label(text="Merah", font_size=42, bold=True, color=(0,0,0,1),
                                 halign='left', valign='bottom')
        self.name_label.bind(size=lambda *_a: setattr(self.name_label, 'text_size', self.name_label.size))
        self.hex_label = Label(text="#FF0000", font_size=30, color=(0.35,0.35,0.35,1),
                                halign='left', valign='top')
        self.hex_label.bind(size=lambda *_a: setattr(self.hex_label, 'text_size', self.hex_label.size))
        text_box.add_widget(self.name_label)
        text_box.add_widget(self.hex_label)
        info_box.add_widget(text_box)
        content.add_widget(info_box)

        # ---- Kartu arti warna ----
        meaning_box = BoxLayout(size_hint=(1, None), height=dp(76), padding=[dp(14), dp(8)])
        add_rounded_card(meaning_box, bg_rgba=(0.94, 0.94, 0.97, 1))
        self.meaning_label = Label(text=COLOR_MEANINGS.get("Merah", ""), font_size=26,
                                    color=(0.25,0.25,0.25,1), halign='left', valign='middle')
        self.meaning_label.bind(size=lambda *_a: setattr(self.meaning_label, 'text_size', self.meaning_label.size))
        meaning_box.add_widget(self.meaning_label)
        content.add_widget(meaning_box)

        # ---- Tombol Hex / Nama / Arti (salin ke clipboard) ----
        # Netral (hitam, border abu tipis) -- sesuai referensi, BUKAN ungu.
        copy_box = BoxLayout(size_hint=(1, None), height=dp(64), spacing=dp(10))
        btn_copy_hex = FlatButton(text="Hex", bg_rgba=(1,1,1,1), border_rgba=(0.7,0.7,0.75,1),
                                   color=(0.1,0.1,0.1,1), bold=False, font_size=28)
        btn_copy_hex.bind(on_release=self.copy_hex)
        btn_copy_name = FlatButton(text="Nama", bg_rgba=(1,1,1,1), border_rgba=(0.7,0.7,0.75,1),
                                    color=(0.1,0.1,0.1,1), bold=False, font_size=28)
        btn_copy_name.bind(on_release=self.copy_name)
        btn_copy_meaning = FlatButton(text="Arti", bg_rgba=(1,1,1,1), border_rgba=(0.7,0.7,0.75,1),
                                       color=(0.1,0.1,0.1,1), bold=False, font_size=28)
        btn_copy_meaning.bind(on_release=self.copy_meaning)
        copy_box.add_widget(btn_copy_hex)
        copy_box.add_widget(btn_copy_name)
        copy_box.add_widget(btn_copy_meaning)
        content.add_widget(copy_box)

        # ---- Nilai Warna (RGB & format lain) ----
        # Header + spinner format KECIL di pojok kanan (bukan kotak
        # "Format Warna: RGB" besar -- referensi tidak punya itu).
        nilai_header = BoxLayout(size_hint=(1, None), height=dp(40), spacing=dp(6))
        self.nilai_title = Label(text="Nilai Warna (RGB)", font_size=32, bold=True, color=(0,0,0,1),
                                  halign='left', valign='bottom')
        self.nilai_title.bind(size=lambda *_a: setattr(self.nilai_title, 'text_size', self.nilai_title.size))
        nilai_header.add_widget(self.nilai_title)
        content.add_widget(nilai_header)

        self.format_panel = ColorFormatPanel(size_hint=(1, None), height=dp(110))
        self.format_panel.on_color_update = self.on_format_update
        self.format_panel.format_spinner.bind(text=self._on_format_spinner_change)
        nilai_header.add_widget(self.format_panel.format_spinner)
        content.add_widget(self.format_panel)

        # ---- Grid warna: satu baris ringkas, polos (tanpa kartu) ----
        grid_row = BoxLayout(size_hint=(1, None), height=dp(60), spacing=dp(10))
        grid_row.add_widget(Label(text="Grid:", font_size=30, bold=True, color=(0,0,0,1), size_hint_x=0.22))
        grid_row.add_widget(Label(text="Cols", font_size=27, color=(0,0,0,1), size_hint_x=0.18))
        self.grad_cols_input = flat_textinput(text="72", input_filter='int', multiline=False, font_size=30,
                                          size_hint_x=0.28, padding_y=[dp(10), dp(10)])
        self.grad_cols_input.bind(text=self.on_grid_change)
        grid_row.add_widget(self.grad_cols_input)
        grid_row.add_widget(Label(text="Rows", font_size=27, color=(0,0,0,1), size_hint_x=0.18))
        self.grad_rows_input = flat_textinput(text="15", input_filter='int', multiline=False, font_size=30,
                                          size_hint_x=0.28, padding_y=[dp(10), dp(10)])
        self.grad_rows_input.bind(text=self.on_grid_change)
        grid_row.add_widget(self.grad_rows_input)
        content.add_widget(grid_row)

        gradasi_title = Label(text="Pembuat Gradasi Warna", font_size=32, bold=True, color=(0,0,0,1),
                               size_hint=(1, None), height=dp(40), halign='left', valign='bottom')
        gradasi_title.bind(size=lambda *_a: setattr(gradasi_title, 'text_size', gradasi_title.size))
        content.add_widget(gradasi_title)

        gradasi_container = BoxLayout(orientation='vertical', size_hint=(1, None),
                                       spacing=dp(10), padding=[0, dp(6)])
        gradasi_container.bind(minimum_height=gradasi_container.setter('height'))

        def _make_warna_slot(default_rgb, label_text, ambil_callback):
            box = BoxLayout(orientation='vertical', size_hint=(0.42, None), spacing=dp(6))
            box.bind(minimum_height=box.setter('height'))
            top_row = BoxLayout(size_hint_y=None, height=dp(64), spacing=dp(8))
            swatch = BoxLayout(size_hint_x=0.4)
            with swatch.canvas:
                swatch_color = Color(*[c/255.0 for c in default_rgb], 1)
                swatch_rect = RoundedRectangle(pos=swatch.pos, size=swatch.size, radius=[dp(10)])

            def _sync_swatch(*_a):
                swatch_rect.pos = swatch.pos
                swatch_rect.size = swatch.size
            swatch.bind(pos=_sync_swatch, size=_sync_swatch)

            btn_ubah = FlatButton(text="Ubah", bg_rgba=(1,1,1,1), border_rgba=ACCENT_PURPLE,
                                   color=ACCENT_PURPLE, bold=True, font_size=26, size_hint_x=0.6)
            btn_ubah.bind(on_release=ambil_callback)
            top_row.add_widget(swatch)
            top_row.add_widget(btn_ubah)
            box.add_widget(Label(text=label_text, font_size=28, color=(0,0,0,1),
                                  size_hint_y=None, height=dp(34)))
            box.add_widget(top_row)
            rgb_row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(52))
            box.add_widget(rgb_row)
            return box, rgb_row, swatch_color

        w1_box, w1_rgb, self._w1_swatch_color = _make_warna_slot((255, 0, 0), "Warna 1", self.ambil_warna1)
        self.grad_r1 = flat_textinput(text="255", hint_text="R", input_filter='int', multiline=False,
                                  font_size=30, halign='center', padding_y=[dp(10), dp(10)])
        self.grad_g1 = flat_textinput(text="0", hint_text="G", input_filter='int', multiline=False,
                                  font_size=30, halign='center', padding_y=[dp(10), dp(10)])
        self.grad_b1 = flat_textinput(text="0", hint_text="B", input_filter='int', multiline=False,
                                  font_size=30, halign='center', padding_y=[dp(10), dp(10)])
        for inp in (self.grad_r1, self.grad_g1, self.grad_b1):
            w1_rgb.add_widget(inp)
            inp.bind(text=self._update_grad_swatches)

        w2_box, w2_rgb, self._w2_swatch_color = _make_warna_slot((0, 0, 255), "Warna 2", self.ambil_warna2)
        self.grad_r2 = flat_textinput(text="0", hint_text="R", input_filter='int', multiline=False,
                                  font_size=30, halign='center', padding_y=[dp(10), dp(10)])
        self.grad_g2 = flat_textinput(text="0", hint_text="G", input_filter='int', multiline=False,
                                  font_size=30, halign='center', padding_y=[dp(10), dp(10)])
        self.grad_b2 = flat_textinput(text="255", hint_text="B", input_filter='int', multiline=False,
                                  font_size=30, halign='center', padding_y=[dp(10), dp(10)])
        for inp in (self.grad_r2, self.grad_g2, self.grad_b2):
            w2_rgb.add_widget(inp)
            inp.bind(text=self._update_grad_swatches)

        gradasi_input = BoxLayout(size_hint=(1, None), spacing=dp(10))
        gradasi_input.bind(minimum_height=gradasi_input.setter('height'))
        gradasi_input.add_widget(w1_box)
        gradasi_input.add_widget(w2_box)
        gradasi_container.add_widget(gradasi_input)

        btn_grad = FlatButton(text="Buat Gradasi", bg_rgba=ACCENT_PURPLE, border_rgba=ACCENT_PURPLE,
                               color=(1,1,1,1), bold=True, font_size=32,
                               size_hint=(1, None), height=dp(60))
        btn_grad.bind(on_release=self.buat_gradasi)
        gradasi_container.add_widget(btn_grad)

        gradasi_hasil = BoxLayout(size_hint=(1, None), height=dp(190))
        self.gradient_ramp = GradientRamp(size_hint=(1, 1), height=390)
        gradasi_hasil.add_widget(self.gradient_ramp)
        gradasi_container.add_widget(gradasi_hasil)
        content.add_widget(gradasi_container)

        # ---- Export Tampilan Penuh (pengganti screenshot panjang) ----
        # Fitur screenshot-panjang bawaan HP tidak bisa membaca konten
        # aplikasi Kivy (dirender ke satu permukaan OpenGL, bukan
        # struktur widget Android asli), jadi selalu berhenti di
        # tengah jalan / salah bilang "sudah sampai dasar". Tombol ini
        # meng-export SENDIRI seluruh halaman ini jadi satu file PNG
        # utuh dari dalam app -- termasuk kotak warna & slider Value
        # yang tetap terlihat (tidak ikut scroll), digabung dengan
        # seluruh isi area yang bisa di-scroll di bawahnya. Latar
        # putih diisi ulang secara eksplisit saat digabung, supaya
        # tidak transparan/hitam seperti kalau widget di-export sendirian.
        export_box = BoxLayout(orientation='vertical', size_hint=(1, None), height=dp(96), spacing=dp(6))
        self.export_status_label = Label(
            text="", font_size=22, color=(0.15, 0.15, 0.15, 1),
            size_hint=(1, None), height=dp(30)
        )
        export_box.add_widget(self.export_status_label)
        export_btn = make_export_button_multi(
            lambda: [self.tab_strip_widget, self.color_square, self.value_layout, self.scroll_content],
            text="\U0001F4F8 Export Tampilan Penuh (PNG)",
            on_status=lambda msg: setattr(self.export_status_label, 'text', msg),
            bg_rgba=(1, 1, 1, 1),
            size_hint=(1, None), height=dp(56), font_size=32
        )
        export_box.add_widget(export_btn)
        content.add_widget(export_box)

        self._save_event = None
        # Muat kerjaan terakhir (warna & pengaturan grid) setelah widget siap
        Clock.schedule_once(self._restore_state, 0)

    def _restore_state(self, dt):
        state = AppState.load_section('halaman1', {})
        cols = state.get('grid_cols')
        rows = state.get('grid_rows')
        if cols and rows:
            try:
                cols = max(2, min(int(cols), 150))
                rows = max(2, min(int(rows), 60))
                self.grad_cols_input.text = str(cols)
                self.grad_rows_input.text = str(rows)
                GridSettings.update(cols, rows)
            except Exception:
                pass
        rgb = state.get('rgb')
        if rgb and len(rgb) == 3:
            try:
                r, g, b = [max(0, min(255, int(v))) for v in rgb]
                self.update_from_rgb(r, g, b)
                return
            except Exception:
                pass
        self.update_from_rgb(255, 0, 0)

    def _schedule_save(self, *args):
        if self._save_event:
            self._save_event.cancel()
        self._save_event = Clock.schedule_once(self._save_state, 0.6)

    def _save_state(self, *args):
        try:
            r = int(self.format_panel.inputs["RGB"][0].text)
            g = int(self.format_panel.inputs["RGB"][1].text)
            b = int(self.format_panel.inputs["RGB"][2].text)
        except Exception:
            return
        try:
            cols = int(self.grad_cols_input.text) if self.grad_cols_input.text else GridSettings.cols
        except Exception:
            cols = GridSettings.cols
        try:
            rows = int(self.grad_rows_input.text) if self.grad_rows_input.text else GridSettings.rows
        except Exception:
            rows = GridSettings.rows
        AppState.save_section('halaman1', {'rgb': [r, g, b], 'grid_cols': cols, 'grid_rows': rows})

    def force_save(self):
        """Dipanggil saat aplikasi ditutup/di-pause agar kerjaan tersimpan langsung."""
        if self._save_event:
            self._save_event.cancel()
            self._save_event = None
        self._save_state()

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def update_rect(self, instance, value):
        self.preview_rect.pos = instance.pos
        self.preview_rect.size = instance.size

    def square_changed(self, hue, saturation, value):
        r, g, b = hsv_to_rgb(hue, saturation, self.value_slider.value)
        self.update_from_rgb(r, g, b)

    def on_value_change(self, value):
        if self._updating:
            return
        val = int(value)
        h = self.color_square.hue
        s = self.color_square.saturation
        r, g, b = hsv_to_rgb(h, s, val)
        self.update_from_rgb(r, g, b)

    def _on_format_spinner_change(self, spinner, text):
        self.nilai_title.text = "Nilai Warna ({})".format(text)

    def on_format_update(self, r, g, b):
        self.update_from_rgb(r, g, b)

    def update_from_rgb(self, r, g, b):
        self._updating = True
        self.format_panel.update_values(r, g, b)
        hex_code = "#{:02X}{:02X}{:02X}".format(r, g, b)
        name = find_nearest_color_name(hex_code)
        meaning = get_color_meaning(name)

        self.preview_color.rgb = (r/255.0, g/255.0, b/255.0)
        self.hex_label.text = hex_code
        self.name_label.text = name
        self.meaning_label.text = meaning

        h, s, v = rgb_to_hsv(r, g, b)
        self.color_square.set_hue_sat(h, s)
        self.value_slider.hue = h
        self.value_slider.saturation = s
        self.value_slider.value = v
        self.value_slider._redraw_track()
        self._updating = False
        self._schedule_save()

    def ambil_warna1(self, instance):
        try:
            r = int(self.format_panel.inputs["RGB"][0].text)
            g = int(self.format_panel.inputs["RGB"][1].text)
            b = int(self.format_panel.inputs["RGB"][2].text)
            self.grad_r1.text = str(r)
            self.grad_g1.text = str(g)
            self.grad_b1.text = str(b)
        except:
            pass

    def ambil_warna2(self, instance):
        try:
            r = int(self.format_panel.inputs["RGB"][0].text)
            g = int(self.format_panel.inputs["RGB"][1].text)
            b = int(self.format_panel.inputs["RGB"][2].text)
            self.grad_r2.text = str(r)
            self.grad_g2.text = str(g)
            self.grad_b2.text = str(b)
        except:
            pass

    def _update_grad_swatches(self, *_args):
        try:
            r1 = max(0, min(255, int(self.grad_r1.text or 0)))
            g1 = max(0, min(255, int(self.grad_g1.text or 0)))
            b1 = max(0, min(255, int(self.grad_b1.text or 0)))
            self._w1_swatch_color.rgb = (r1/255.0, g1/255.0, b1/255.0)
        except Exception:
            pass
        try:
            r2 = max(0, min(255, int(self.grad_r2.text or 0)))
            g2 = max(0, min(255, int(self.grad_g2.text or 0)))
            b2 = max(0, min(255, int(self.grad_b2.text or 0)))
            self._w2_swatch_color.rgb = (r2/255.0, g2/255.0, b2/255.0)
        except Exception:
            pass

    def buat_gradasi(self, instance):
        try:
            r1 = int(self.grad_r1.text)
            g1 = int(self.grad_g1.text)
            b1 = int(self.grad_b1.text)
            r2 = int(self.grad_r2.text)
            g2 = int(self.grad_g2.text)
            b2 = int(self.grad_b2.text)
            r1 = max(0, min(255, r1)); g1 = max(0, min(255, g1)); b1 = max(0, min(255, b1))
            r2 = max(0, min(255, r2)); g2 = max(0, min(255, g2)); b2 = max(0, min(255, b2))
        except:
            return
        self.gradient_ramp.set_colors(r1, g1, b1, r2, g2, b2)

    def copy_hex(self, instance):
        Clipboard.copy(self.hex_label.text)

    def copy_name(self, instance):
        Clipboard.copy(self.name_label.text)

    def copy_meaning(self, instance):
        Clipboard.copy(self.meaning_label.text)

    def on_grid_change(self, instance, value):
        try:
            cols = int(self.grad_cols_input.text) if self.grad_cols_input.text else 2
        except ValueError:
            cols = 2
        try:
            rows = int(self.grad_rows_input.text) if self.grad_rows_input.text else 2
        except ValueError:
            rows = 2
        cols = max(2, min(cols, 150))
        rows = max(2, min(rows, 60))
        GridSettings.update(cols, rows)
        self._schedule_save()

# ======================== Halaman 2: Color Gear + Palet =========================
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.slider import Slider
from kivy.core.clipboard import Clipboard
from kivy.uix.spinner import Spinner
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.clock import Clock
from kivy.utils import platform
import os
from datetime import datetime

# Import PIL dengan alias
try:
    from PIL import Image as PILImage
    from PIL import ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

class ColorGearTab(TabbedPanelItem):
    def __init__(self, **kwargs):
        super().__init__(text="Color Gear", **kwargs)

        # Seluruh halaman di-scroll jadi satu (sama seperti referensi:
        # Mode Harmoni, kotak warna, kartu hasil, tombol, sampai daftar
        # palet semuanya ikut ter-scroll bersama, bukan dipaksa muat 1 layar).
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, bar_width=dp(6))
        with scroll.canvas.before:
            # Latar halaman abu muda (bukan putih polos) -- supaya kartu
            # putih (hasil warna & daftar palet) kelihatan berlapis, sama
            # seperti referensi.
            Color(0.933, 0.933, 0.945, 1)
            self.bg_rect = Rectangle(pos=scroll.pos, size=scroll.size)
        scroll.bind(pos=self._update_bg, size=self._update_bg)

        self.content = scroll
        body = BoxLayout(orientation='vertical', size_hint_y=None,
                          padding=dp(16), spacing=dp(16))
        body.bind(minimum_height=body.setter('height'))
        scroll.add_widget(body)

        # --- Mode harmoni: judul di atas, kotak putih bulat + chevron ---
        mode_box = BoxLayout(orientation='vertical', size_hint=(1, None),
                              height=dp(94), spacing=dp(8))
        mode_box.add_widget(Label(text="Mode Harmoni", font_size=30, bold=True,
                                   color=(0.1,0.1,0.1,1), size_hint=(1, None),
                                   height=dp(34), halign='left', valign='bottom',
                                   text_size=(Window.width - dp(32), dp(34))))
        spinner_wrap = RelativeLayout(size_hint=(1, None), height=dp(52))
        self.mode_spinner = Spinner(
            text="Triadik",
            values=("Monokromatik", "Komplementer", "Split-Komplementer", "Analog", "Triadik", "Tetradik", "Kuadrat"),
            size_hint=(1, 1),
            font_size=28,
            halign='left',
            padding=(dp(16), 0),
            background_normal='',
            background_down='',
            background_color=(1, 1, 1, 1),
            color=(0.1, 0.1, 0.1, 1),
        )
        with self.mode_spinner.canvas.after:
            Color(0.75, 0.75, 0.8, 1)
            self._spinner_border = Line(width=dp(1.2))

        def _sync_spinner_border(*_a):
            self._spinner_border.rounded_rectangle = (
                self.mode_spinner.x, self.mode_spinner.y,
                self.mode_spinner.width, self.mode_spinner.height, dp(12))
        self.mode_spinner.bind(pos=_sync_spinner_border, size=_sync_spinner_border)
        self.mode_spinner.bind(text=self.on_mode_change)
        spinner_wrap.add_widget(self.mode_spinner)
        chevron = Label(text=">", font_size=26, color=(0.4,0.4,0.4,1),
                         size_hint=(None, None), size=(dp(30), dp(30)),
                         pos_hint={'right': 0.97, 'center_y': 0.5})
        spinner_wrap.add_widget(chevron)
        mode_box.add_widget(spinner_wrap)
        body.add_widget(mode_box)

        # --- ColorSquareMini utama ---
        self.main_square = ColorSquareMini(size_hint=(1, None), height=dp(300))
        self.main_square.on_color_changed = self.update_harmony
        body.add_widget(self.main_square)

        # --- 3 hasil harmoni: kartu putih bulat berisi swatch + nama (bold) + hex (abu) ---
        grid = GridLayout(cols=3, spacing=dp(12), size_hint=(1, None), height=dp(190))
        self.color_infos = []
        for i in range(3):
            card = BoxLayout(orientation='vertical', spacing=dp(6), padding=dp(10))
            add_rounded_card(card, bg_rgba=(1, 1, 1, 1), radius=dp(16))
            preview = BoxLayout(size_hint=(1, None), height=dp(96))
            with preview.canvas:
                preview_color = Color(1, 0, 0, 1)
                preview_rect = RoundedRectangle(pos=preview.pos, size=preview.size, radius=[dp(14)])
            preview.bind(pos=self._update_preview_rect(preview_rect, preview),
                         size=self._update_preview_rect(preview_rect, preview))
            card.add_widget(preview)
            name_label = Label(text="Merah", font_size=24, bold=True, color=(0,0,0,1),
                                size_hint=(1, None), height=dp(28))
            hex_label = Label(text="#FF0000", font_size=19, color=(0.4,0.4,0.4,1),
                               size_hint=(1, None), height=dp(22))
            card.add_widget(name_label)
            card.add_widget(hex_label)
            grid.add_widget(card)
            self.color_infos.append({
                'preview': preview,
                'preview_color': preview_color,
                'preview_rect': preview_rect,
                'hex': hex_label,
                'name': name_label
            })
        body.add_widget(grid)

        # --- Tombol aksi: Salin HEX (navy) & Simpan Palet (abu) ---
        action_box = BoxLayout(size_hint=(1, None), height=dp(60), spacing=dp(14))
        btn_copy = FlatButton(text="Salin HEX", font_size=26, bold=True,
                               bg_rgba=get_color_from_hex('#123A5C'),
                               border_rgba=get_color_from_hex('#123A5C'),
                               color=(1,1,1,1))
        btn_copy.bind(on_release=self.copy_all_hex)
        btn_save = FlatButton(text="Simpan Palet", font_size=26, bold=True,
                               bg_rgba=(0.42, 0.44, 0.47, 1),
                               border_rgba=(0.42, 0.44, 0.47, 1),
                               color=(1,1,1,1))
        btn_save.bind(on_release=self.save_palette)
        action_box.add_widget(btn_copy)
        action_box.add_widget(btn_save)
        body.add_widget(action_box)

        # --- Bagian Palet ---
        adv_label = Label(text="Pengaturan Lanjutan", font_size=26, bold=True,
                           color=(0.1,0.1,0.1,1), size_hint=(1, None), height=dp(36),
                           halign='center', valign='middle')
        adv_label.bind(size=lambda *_a: setattr(adv_label, 'text_size', adv_label.size))
        body.add_widget(adv_label)

        btn_add_palette = FlatButton(text="Tambah Palet", size_hint=(1, None), height=dp(58),
                                      font_size=26, bold=True,
                                      bg_rgba=(0.42, 0.44, 0.47, 1),
                                      border_rgba=(0.42, 0.44, 0.47, 1),
                                      color=(1,1,1,1))
        btn_add_palette.bind(on_release=self.add_palette)
        body.add_widget(btn_add_palette)

        # Daftar palet -- ikut scroll bersama body (bukan scroll bersarang)
        self.palette_list = GridLayout(cols=1, spacing=dp(16), size_hint=(1, None))
        self.palette_list.bind(minimum_height=self.palette_list.setter('height'))
        body.add_widget(self.palette_list)

        # --- Tombol Save All JPG ---
        btn_save_image = FlatButton(text="Simpan Keseluruhan Palet", size_hint=(1, None), height=dp(58),
                                     font_size=26, bold=True,
                                     bg_rgba=(0.42, 0.44, 0.47, 1),
                                     border_rgba=(0.42, 0.44, 0.47, 1),
                                     color=(1,1,1,1))
        btn_save_image.bind(on_release=self.save_all_palettes_as_jpg)
        body.add_widget(btn_save_image)

        self.palettes = []
        self._save_event = None
        Clock.schedule_once(self.init_colors, 0.1)

    # ====================== Fungsi dasar ======================
    def _update_bg(self, *args):
        self.bg_rect.pos = self.content.pos
        self.bg_rect.size = self.content.size

    def _update_preview_rect(self, rect, widget):
        def callback(instance, value):
            rect.pos = widget.pos
            rect.size = widget.size
        return callback

    def init_colors(self, dt):
        # Muat kerjaan terakhir: mode harmoni, warna utama, dan semua palet
        state = AppState.load_section('halaman2', {})
        mode = state.get('mode')
        if mode and mode in self.mode_spinner.values:
            self.mode_spinner.text = mode

        h, s, v = 0, 100, 100
        hsv = state.get('main_hsv')
        if hsv and len(hsv) == 3:
            try:
                h, s, v = hsv[0], hsv[1], hsv[2]
            except Exception:
                h, s, v = 0, 100, 100

        saved_palettes = state.get('palettes')
        if saved_palettes:
            try:
                self.palettes = [
                    {'name': p.get('name', 'Palette'),
                     'colors': [tuple(c) for c in p.get('colors', [])]}
                    for p in saved_palettes
                ]
            except Exception:
                self.palettes = []
            self.refresh_palette_list()

        self.main_square.hue = h
        self.main_square.saturation = s
        self.main_square.value = v
        self.main_square.draw_indicator()
        self.update_harmony(h, s, v)

    def on_mode_change(self, spinner, text):
        self.update_harmony(self.main_square.hue, self.main_square.saturation, self.main_square.value)
        self._schedule_save()

    def _schedule_save(self, *args):
        if self._save_event:
            self._save_event.cancel()
        self._save_event = Clock.schedule_once(self._save_state, 0.6)

    def _save_state(self, *args):
        AppState.save_section('halaman2', {
            'mode': self.mode_spinner.text,
            'main_hsv': [self.main_square.hue, self.main_square.saturation, self.main_square.value],
            'palettes': [{'name': p['name'], 'colors': [list(c) for c in p['colors']]} for p in self.palettes]
        })

    def force_save(self):
        """Dipanggil saat aplikasi ditutup/di-pause agar kerjaan tersimpan langsung."""
        if self._save_event:
            self._save_event.cancel()
            self._save_event = None
        self._save_state()

    def update_harmony(self, h, s, v):
        mode = self.mode_spinner.text
        colors = []
        if mode == "Monokromatik":
            colors = [(h, s, v), (h, max(0, s-30), v), (h, max(0, s-60), v)]
        elif mode == "Komplementer":
            h2 = (h + 180) % 360
            colors = [(h, s, v), (h2, s, v), (h2, s, v)]
        elif mode == "Split-Komplementer":
            h2 = (h + 150) % 360
            h3 = (h + 210) % 360
            colors = [(h, s, v), (h2, s, v), (h3, s, v)]
        elif mode == "Analog":
            h2 = (h + 30) % 360
            h3 = (h + 60) % 360
            colors = [(h, s, v), (h2, s, v), (h3, s, v)]
        elif mode == "Triadik":
            h2 = (h + 120) % 360
            h3 = (h + 240) % 360
            colors = [(h, s, v), (h2, s, v), (h3, s, v)]
        elif mode == "Tetradik" or mode == "Kuadrat":
            h2 = (h + 90) % 360
            h3 = (h + 180) % 360
            colors = [(h, s, v), (h2, s, v), (h3, s, v)]
        else:
            h2 = (h + 120) % 360
            h3 = (h + 240) % 360
            colors = [(h, s, v), (h2, s, v), (h3, s, v)]

        for i, (hue, sat, val) in enumerate(colors):
            r, g, b = hsv_to_rgb(hue, sat, val)
            hex_code = "#{:02X}{:02X}{:02X}".format(r, g, b)
            name = find_nearest_color_name(hex_code)
            info = self.color_infos[i]
            info['preview_color'].rgb = (r/255.0, g/255.0, b/255.0)
            info['hex'].text = hex_code
            info['name'].text = name
        self._schedule_save()

    def copy_all_hex(self, instance):
        hexes = [info['hex'].text for info in self.color_infos]
        Clipboard.copy(" | ".join(hexes))

    def get_current_colors(self):
        colors = []
        for info in self.color_infos:
            hex_str = info['hex'].text
            if hex_str.startswith('#'):
                r = int(hex_str[1:3], 16)
                g = int(hex_str[3:5], 16)
                b = int(hex_str[5:7], 16)
                colors.append((r, g, b))
        return colors

    # ====================== Manajemen Palet ======================
    def save_palette(self, instance):
        colors = self.get_current_colors()
        if not colors:
            return
        idx = 1
        names = [p['name'] for p in self.palettes]
        while f"Palette {idx}" in names:
            idx += 1
        name = f"Palette {idx}"
        self.add_palette(None, name=name, colors=colors)

    def add_palette(self, instance, name="Palette Baru", colors=None):
        if colors is None:
            colors = []
        if name == "Palette Baru":
            idx = 1
            names = [p['name'] for p in self.palettes]
            while f"Palette {idx}" in names:
                idx += 1
            name = f"Palette {idx}"
        palet = {'name': name, 'colors': colors}
        self.palettes.append(palet)
        self.refresh_palette_list()
        self._schedule_save()

    # ====================== UI DAFTAR PALET ======================
    def refresh_palette_list(self):
        self.palette_list.clear_widgets()

        for idx, palet in enumerate(self.palettes):
            num_colors = len(palet['colors'])
            rows = (num_colors - 1) // 6 + 1 if num_colors > 0 else 1
            card_height = dp(110) + max(1, rows) * dp(120)
            card = BoxLayout(orientation='vertical', size_hint=(1, None),
                              height=card_height, padding=dp(14), spacing=dp(10))
            add_rounded_card(card, bg_rgba=(1, 1, 1, 1), radius=dp(16))

            top_box = BoxLayout(size_hint=(1, None), height=dp(76), spacing=dp(6))
            name_label = Label(text=palet['name'], font_size=52, bold=True, color=(0,0,0,1),
                                size_hint_x=0.4, halign='left', valign='middle')
            name_label.bind(size=lambda lbl, *_a: setattr(lbl, 'text_size', lbl.size))

            def _icon_btn(icon_text, label_text):
                b = FlatButton(text="{}  {}".format(icon_text, label_text), font_size=40,
                                bold=False, color=(0.1,0.1,0.1,1),
                                bg_rgba=(1,1,1,1), border_rgba=(1,1,1,1),
                                size_hint_x=0.2)
                return b

            btn_save_single = _icon_btn("\U0001F4BE", "Save")
            btn_save_single.bind(on_release=lambda b, p=palet, n=palet['name']: self.save_single_palette_as_jpg(p, n))
            btn_edit = _icon_btn("\u270F", "Edit")
            btn_edit.bind(on_release=lambda b, idx=idx: self.edit_palette(idx))
            btn_delete = _icon_btn("\U0001F5D1", "Hapus")
            btn_delete.color = get_color_from_hex('#B3261E')
            btn_delete.bind(on_release=lambda b, idx=idx: self.delete_palette(idx))

            top_box.add_widget(name_label)
            top_box.add_widget(btn_save_single)
            top_box.add_widget(btn_edit)
            top_box.add_widget(btn_delete)
            card.add_widget(top_box)

            if num_colors > 0:
                color_grid = GridLayout(cols=6, spacing=dp(8), size_hint=(1, None))
                color_grid.bind(minimum_height=color_grid.setter('height'))
                for i, (r, g, b) in enumerate(palet['colors']):
                    slot = BoxLayout(orientation='vertical', size_hint=(1/6, None), height=dp(116), spacing=dp(4))
                    btn_color = FlatButton(text="", bg_rgba=(r/255.0, g/255.0, b/255.0, 1),
                                            border_rgba=(r/255.0, g/255.0, b/255.0, 1),
                                            radius=dp(10), size_hint=(1, None), height=dp(70))
                    btn_color.bind(on_release=lambda b, r=r, g=g, b_c=b: self.show_color_info(r, g, b_c))
                    slot.add_widget(btn_color)
                    hex_text = "#{:02X}{:02X}{:02X}".format(r, g, b)
                    lbl = Label(text=hex_text, font_size=26, color=(0.4,0.4,0.4,1),
                                size_hint=(1, None), height=dp(40))
                    slot.add_widget(lbl)
                    color_grid.add_widget(slot)
                card.add_widget(color_grid)
            else:
                empty_label = Label(text="Tidak ada warna", font_size=44, color=(0.5,0.5,0.5,1),
                                     size_hint=(1, None), height=dp(80))
                card.add_widget(empty_label)

            self.palette_list.add_widget(card)

    def delete_palette(self, idx):
        del self.palettes[idx]
        self.refresh_palette_list()
        self._schedule_save()

    def _update_card_bg(self, widget):
        def callback(instance, value):
            for child in widget.canvas.before.children:
                if isinstance(child, Rectangle):
                    child.pos = widget.pos
                    child.size = widget.size
                    break
        return callback

    def _update_preview_rect_pos(self, widget):
        def callback(instance, value):
            for child in widget.canvas.get_group(None):
                if isinstance(child, Rectangle):
                    child.pos = widget.pos
                    child.size = widget.size
                    break
        return callback

    # ====================== Edit Palet dengan live preview ======================
    def edit_palette(self, idx):
        palet = self.palettes[idx]
        content = BoxLayout(orientation='vertical', spacing=15, padding=15)
        with content.canvas.before:
            Color(1, 1, 1, 1)
            Rectangle(pos=content.pos, size=content.size)
        content.bind(pos=self._update_content_bg(content), size=self._update_content_bg(content))

        name_box = BoxLayout(size_hint_y=0.08, spacing=15)
        name_box.add_widget(Label(text="Nama :", size_hint_x=0.2, font_size=39, color=(0,0,0,1)))
        name_input = TextInput(text=palet['name'], multiline=False, size_hint_x=0.8, font_size=39)
        name_box.add_widget(name_input)
        content.add_widget(name_box)

        slot_grid = GridLayout(cols=6, spacing=10, size_hint_y=0.6)
        slot_grid.bind(minimum_height=slot_grid.setter('height'))
        content.add_widget(slot_grid)

        btn_add_slot = Button(text="Tambah Slot", size_hint_y=0.08, font_size=47)
        content.add_widget(btn_add_slot)

        btn_save = Button(text="Simpan", size_hint_y=0.08, font_size=47, background_color=(0.2,0.6,0.9,1), color=(1,1,1,1))
        content.add_widget(btn_save)

        popup = Popup(title="Edit Palet", content=content, size_hint=(0.9, 0.9))

        def create_color_slot(r, g, b, slot_idx, has_color=True):
            box = BoxLayout(orientation='vertical', size_hint_x=1/6, spacing=3)
            if has_color:
                btn = Button(text="", background_normal='', background_color=(r/255.0, g/255.0, b/255.0, 1), size_hint_y=0.6)
                brightness = (r*0.299 + g*0.587 + b*0.114) / 255
                btn.color = (0,0,0,1) if brightness > 0.5 else (1,1,1,1)
                hex_text = "#{:02X}{:02X}{:02X}".format(r, g, b)
            else:
                btn = Button(text="+", font_size=43, background_normal='', background_color=(0.95, 0.95, 0.95, 1), size_hint_y=0.6)
                btn.color = (0,0,0,1)
                hex_text = "Kosong"
            btn.bind(on_press=lambda b, idx=slot_idx: pick_color(idx))
            box.add_widget(btn)

            lbl_hex = Label(text=hex_text, font_size=25, color=(0.2,0.2,0.2,1), size_hint_y=0.2)
            box.add_widget(lbl_hex)

            if has_color:
                btn_del = Button(text="✖", size_hint_y=0.2, font_size=16, background_normal='', background_color=(0.9,0.2,0.2,1), color=(1,1,1,1))
                btn_del.bind(on_press=lambda b, idx=slot_idx: remove_color(idx))
                box.add_widget(btn_del)
            else:
                lbl = Label(text="", size_hint_y=0.2)
                box.add_widget(lbl)
            return box

        def refresh_slots():
            slot_grid.clear_widgets()
            total_slots = 15
            for i in range(total_slots):
                if i < len(palet['colors']):
                    r, g, b = palet['colors'][i]
                    box = create_color_slot(r, g, b, i, True)
                else:
                    box = create_color_slot(0, 0, 0, i, False)
                slot_grid.add_widget(box)
            slot_grid.height = (len(palet['colors']) // 6 + 1) * 120

        # ====== FITUR LIVE PREVIEW DI POPUP PICKER ======
        def pick_color(slot_idx):
            picker_content = BoxLayout(orientation='vertical', spacing=10, padding=10)
            with picker_content.canvas.before:
                Color(1, 1, 1, 1)
                Rectangle(pos=picker_content.pos, size=picker_content.size)
            picker_content.bind(pos=self._update_picker_bg(picker_content), size=self._update_picker_bg(picker_content))

            # Color picker utama
            picker = ColorSquareMini(size_hint=(1, 0.55))
            if slot_idx < len(palet['colors']):
                r, g, b = palet['colors'][slot_idx]
                h, s, v = rgb_to_hsv(r, g, b)
                picker.hue = h
                picker.saturation = s
                picker.value = v
            else:
                picker.hue = 0
                picker.saturation = 100
                picker.value = 100
            picker.draw_indicator()
            picker_content.add_widget(picker)

            # Slider Value
            slider_box = BoxLayout(size_hint=(1, 0.12), spacing=10)
            slider_box.add_widget(Label(text="Value", size_hint_x=0.2, font_size=37, color=(0,0,0,1)))
            slider = Slider(min=0, max=100, value=picker.value, step=1)
            label_val = Label(text=str(picker.value), size_hint_x=0.15, font_size=20, color=(0,0,0,1))
            slider_box.add_widget(slider)
            slider_box.add_widget(label_val)
            picker_content.add_widget(slider_box)

            # ==== LIVE PREVIEW Warna ====
            preview_box = BoxLayout(size_hint=(1, 0.12), spacing=10)
            preview_box.add_widget(Label(text="Preview:", font_size=37, color=(0,0,0,1), size_hint_x=0.2))
            preview = BoxLayout(size_hint_x=0.25)
            with preview.canvas:
                r_cur, g_cur, b_cur = hsv_to_rgb(picker.hue, picker.saturation, picker.value)
                preview_color = Color(r_cur/255.0, g_cur/255.0, b_cur/255.0, 1)
                preview_rect = Rectangle(pos=preview.pos, size=preview.size)
            preview.bind(pos=self._update_preview_rect_pos(preview), size=self._update_preview_rect_pos(preview))
            preview_box.add_widget(preview)
            info_label = Label(text="", font_size=41, color=(0,0,0,1), size_hint_x=0.55)
            preview_box.add_widget(info_label)
            picker_content.add_widget(preview_box)

            # Fungsi update preview
            def update_preview(h, s, v):
                r, g, b = hsv_to_rgb(h, s, v)
                preview_color.rgb = (r/255.0, g/255.0, b/255.0)
                hex_code = "#{:02X}{:02X}{:02X}".format(r, g, b)
                name = find_nearest_color_name(hex_code)
                info_label.text = f"{hex_code}  {name}"

            # Binding event
            def on_picker_change(h, s, v):
                slider.value = v
                label_val.text = str(int(v))
                update_preview(h, s, v)

            def on_slider_change(inst, val):
                val = int(val)
                label_val.text = str(val)
                picker.value = val
                picker.draw_indicator()
                update_preview(picker.hue, picker.saturation, val)

            picker.on_color_changed = on_picker_change
            slider.bind(value=on_slider_change)

            # Inisialisasi preview pertama kali
            update_preview(picker.hue, picker.saturation, picker.value)

            # Tombol OK / Batal
            btn_box = BoxLayout(size_hint=(1, 0.12), spacing=10)
            btn_ok = Button(text="OK", font_size=45, background_color=(0.2,0.6,0.9,1), color=(1,1,1,1))
            btn_cancel = Button(text="Batal", font_size=45)
            btn_box.add_widget(btn_cancel)
            btn_box.add_widget(btn_ok)
            picker_content.add_widget(btn_box)

            picker_popup = Popup(title="Pilih Warna", content=picker_content, size_hint=(0.8, 0.8))

            def on_ok(btn):
                val = int(slider.value)
                r, g, b = hsv_to_rgb(picker.hue, picker.saturation, val)
                if slot_idx < len(palet['colors']):
                    palet['colors'][slot_idx] = (r, g, b)
                else:
                    if len(palet['colors']) < 15:
                        palet['colors'].insert(slot_idx, (r, g, b))
                    else:
                        palet['colors'][-1] = (r, g, b)
                refresh_slots()
                picker_popup.dismiss()

            def on_cancel(btn):
                picker_popup.dismiss()

            btn_ok.bind(on_press=on_ok)
            btn_cancel.bind(on_press=on_cancel)
            picker_popup.open()

        def remove_color(idx):
            if idx < len(palet['colors']):
                del palet['colors'][idx]
            refresh_slots()

        def add_slot(instance):
            if len(palet['colors']) < 15:
                palet['colors'].append((220, 220, 220))
            refresh_slots()

        def save_palette(instance):
            palet['name'] = name_input.text
            popup.dismiss()
            self.refresh_palette_list()
            self._schedule_save()

        btn_add_slot.bind(on_press=add_slot)
        btn_save.bind(on_press=save_palette)
        refresh_slots()
        popup.open()

    def _update_content_bg(self, widget):
        def callback(instance, value):
            for child in widget.canvas.before.children:
                if isinstance(child, Rectangle):
                    child.pos = widget.pos
                    child.size = widget.size
                    break
        return callback

    def _update_picker_bg(self, widget):
        def callback(instance, value):
            for child in widget.canvas.before.children:
                if isinstance(child, Rectangle):
                    child.pos = widget.pos
                    child.size = widget.size
                    break
        return callback

    # ====================== POPUP INFORMASI WARNA (kotak lebih tinggi, font pas) ======================
    def show_color_info(self, r, g, b):
        hex_code = "#{:02X}{:02X}{:02X}".format(r, g, b)
        cmyk = rgb_to_cmyk(r, g, b)
        lab = rgb_to_lab(r, g, b)
        hsv = rgb_to_hsv(r, g, b)
        hsl = rgb_to_hsl(r, g, b)
        name = find_nearest_color_name(hex_code)
        meaning = get_color_meaning(name)

        content = BoxLayout(orientation='vertical', spacing=25, padding=30)
        with content.canvas.before:
            Color(1, 1, 1, 1)
            Rectangle(pos=content.pos, size=content.size)
        content.bind(pos=self._update_content_bg(content), size=self._update_content_bg(content))

        # Preview dan nama
        preview_box = BoxLayout(size_hint_y=0.12, spacing=25)
        preview = BoxLayout(size_hint_x=0.25)
        with preview.canvas:
            Color(r/255.0, g/255.0, b/255.0, 1)
            Rectangle(pos=preview.pos, size=preview.size)
        preview.bind(pos=self._update_preview_rect_info(preview), size=self._update_preview_rect_info(preview))
        preview_box.add_widget(preview)

        text_box = BoxLayout(orientation='vertical', size_hint_x=0.75)
        name_label = Label(text=name, font_size=50, bold=True, color=(0,0,0,1), halign='left')
        meaning_label = Label(
            text=meaning,
            font_size=40,
            italic=True,
            color=(0.2,0.2,0.2,1),
            halign='left',
            text_size=(self.content.width * 0.7, None),
            size_hint_y=None,
            height=150
        )
        meaning_label.bind(size=lambda lbl, val: setattr(lbl, 'text_size', (lbl.width, None)))
        text_box.add_widget(name_label)
        text_box.add_widget(meaning_label)
        preview_box.add_widget(text_box)
        content.add_widget(preview_box)

        # Grid format warna - perbesar ukuran kotak (height=160) dan font lebih kecil
        grid = GridLayout(cols=2, spacing=25, size_hint_y=0.78)
        formats = [
            ("HEX", hex_code),
            ("RGB", f"{r}, {g}, {b}"),
            ("CMYK", f"{cmyk[0]}%, {cmyk[1]}%, {cmyk[2]}%, {cmyk[3]}%"),
            ("LAB", f"L: {lab[0]}, a: {lab[1]}, b: {lab[2]}"),
            ("HSV", f"H: {hsv[0]}°, S: {hsv[1]}%, V: {hsv[2]}%"),
            ("HSL", f"H: {hsl[0]}°, S: {hsl[1]}%, L: {hsl[2]}%")
        ]
        for label, value in formats:
            box = BoxLayout(orientation='vertical', size_hint_y=None, height=160)  # lebih tinggi
            label_widget = Label(text=label, font_size=34, bold=True, color=(0,0,0,1))
            box.add_widget(label_widget)
            btn = Button(
                text=value,
                font_size=32,  # lebih kecil agar muat
                background_color=(0.1, 0.3, 0.6, 1),
                color=(1, 1, 1, 1),
                size_hint_y=0.65,
                text_size=(box.width, None),
                halign='center',
                valign='middle'
            )
            # Binding untuk update text_size saat lebar berubah
            def bind_text_size(instance, val):
                instance.text_size = (instance.width, None)
            btn.bind(size=bind_text_size)
            btn.bind(on_press=lambda b, val=value: Clipboard.copy(val))
            box.add_widget(btn)
            grid.add_widget(box)
        content.add_widget(grid)

        # Tombol Tutup
        btn_close = Button(
            text="Tutup",
            size_hint_y=0.1,
            font_size=50,
            background_color=(0.2,0.6,0.9,1),
            color=(1,1,1,1)
        )
        popup = Popup(title="Informasi Warna", content=content, size_hint=(0.85, 0.85))
        btn_close.bind(on_press=popup.dismiss)
        content.add_widget(btn_close)
        popup.open()

    def _update_preview_rect_info(self, widget):
        def callback(instance, value):
            for child in widget.canvas.get_group(None):
                if isinstance(child, Rectangle):
                    child.pos = widget.pos
                    child.size = widget.size
                    break
        return callback

    # ====================== Save Single Palette ======================
    def save_single_palette_as_jpg(self, palet, palet_name):
        if not HAS_PIL:
            self.show_message("PIL (Pillow) tidak terinstal. Install dengan 'pip install Pillow'")
            return
        if not palet['colors']:
            self.show_message("Palet tidak memiliki warna.")
            return

        folder_name = "Pallet Color Ramp"
        save_folder = None

        if platform == 'android':
            try:
                from android.storage import primary_external_storage_path
                base = primary_external_storage_path()
                if base:
                    pics = os.path.join(base, 'Pictures', folder_name)
                    if not os.path.exists(pics):
                        try:
                            os.makedirs(pics, exist_ok=True)
                            save_folder = pics
                        except:
                            down = os.path.join(base, 'Download', folder_name)
                            if not os.path.exists(down):
                                try:
                                    os.makedirs(down, exist_ok=True)
                                    save_folder = down
                                except:
                                    save_folder = os.path.join(os.getcwd(), folder_name)
                            else:
                                save_folder = down
                    else:
                        save_folder = pics
                else:
                    raise Exception("No external storage")
            except:
                ext = os.environ.get('EXTERNAL_STORAGE', '/storage/emulated/0')
                pics = os.path.join(ext, 'Pictures', folder_name)
                if not os.path.exists(pics):
                    try:
                        os.makedirs(pics, exist_ok=True)
                        save_folder = pics
                    except:
                        down = os.path.join(ext, 'Download', folder_name)
                        if not os.path.exists(down):
                            try:
                                os.makedirs(down, exist_ok=True)
                                save_folder = down
                            except:
                                save_folder = os.path.join(os.getcwd(), folder_name)
                        else:
                            save_folder = down
                else:
                    save_folder = pics
        else:
            try:
                from plyer import filechooser
                filechooser.choose_dir(on_selection=self._save_single_palette_to_path)
                return
            except:
                try:
                    import tkinter as tk
                    from tkinter import filedialog
                    root = tk.Tk()
                    root.withdraw()
                    folder = filedialog.askdirectory(title="Pilih folder untuk menyimpan gambar palet")
                    root.destroy()
                    if folder:
                        target = os.path.join(folder, folder_name)
                        if not os.path.exists(target):
                            os.makedirs(target, exist_ok=True)
                        self._save_single_palette_to_path([target], palet, palet_name)
                    else:
                        self.show_message("Penyimpanan dibatalkan.")
                    return
                except:
                    folder = os.getcwd()
                    target = os.path.join(folder, folder_name)
                    if not os.path.exists(target):
                        os.makedirs(target, exist_ok=True)
                    self._save_single_palette_to_path([target], palet, palet_name)
                    self.show_message(f"Tidak dapat membuka dialog folder. Disimpan di:\n{target}")
                    return

        if save_folder:
            if not os.path.exists(save_folder):
                try:
                    os.makedirs(save_folder, exist_ok=True)
                except:
                    save_folder = os.path.join(os.getcwd(), folder_name)
                    os.makedirs(save_folder, exist_ok=True)
            self._save_single_palette_to_path([save_folder], palet, palet_name)
        else:
            fallback = os.path.join(os.getcwd(), folder_name)
            if not os.path.exists(fallback):
                os.makedirs(fallback, exist_ok=True)
            self._save_single_palette_to_path([fallback], palet, palet_name)

    def _save_single_palette_to_path(self, selected_paths, palet, palet_name):
        if not selected_paths:
            return
        folder = selected_paths[0]
        if not os.path.exists(folder):
            try:
                os.makedirs(folder, exist_ok=True)
            except:
                folder = os.getcwd()
        safe_name = "".join(c for c in palet_name if c.isalnum() or c in (' ', '_')).replace(' ', '_')
        filename = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(folder, filename)
        try:
            self._generate_single_palette_image(filepath, palet, palet_name)
            self.show_message(f"✅ Palet '{palet_name}' berhasil disimpan di:\n{filepath}")
        except Exception as e:
            self.show_message(f"❌ Gagal menyimpan: {str(e)}")

    def _get_font(self, size):
        """
        Coba beberapa font TrueType lintas platform (Windows/Linux/Android/Mac)
        supaya ukuran font benar-benar terpakai. 'arial.ttf' sering TIDAK ada
        di Android/Linux sehingga PIL diam-diam jatuh ke font default berukuran
        sangat kecil dan mengabaikan ukuran yang diminta -- inilah sebab judul
        & kode warna tampak kecil pada gambar hasil simpan.
        """
        font_candidates = [
            "arialbd.ttf", "arial.ttf",
            "/system/fonts/Roboto-Bold.ttf",
            "/system/fonts/Roboto-Medium.ttf",
            "/system/fonts/DroidSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf",
        ]
        for path in font_candidates:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()

    def _generate_single_palette_image(self, filepath, palet, palet_name):
        colors = palet['colors']
        if not colors:
            raise Exception("Tidak ada warna pada palet.")
        width = 2400
        scale = width / 900
        box_size = int(110 * scale)
        title_font_size = int(box_size * 0.34)
        hex_font_size = int(box_size * 0.24)
        margin = int(30 * scale)
        spacing = int(14 * scale)
        cols = 6
        per_row_height = box_size + hex_font_size + 14

        rows = (len(colors) - 1) // cols + 1
        total_height = margin + title_font_size + 20 + rows * (per_row_height + spacing) + margin

        img = PILImage.new('RGB', (width, total_height), color=(255,255,255))
        draw = ImageDraw.Draw(img)
        font_title = self._get_font(title_font_size)
        font_hex = self._get_font(hex_font_size)

        y = margin
        draw.text((margin, y), palet_name, fill=(0,0,0), font=font_title)
        y += title_font_size + 20
        x = margin
        for i, (r, g, b) in enumerate(colors):
            if i > 0 and i % cols == 0:
                y += per_row_height + spacing
                x = margin
            draw.rectangle([x, y, x+box_size, y+box_size], fill=(r,g,b), outline=(0,0,0), width=2)
            hex_text = "#{:02X}{:02X}{:02X}".format(r, g, b)
            draw.text((x, y + box_size + 6), hex_text, fill=(0,0,0), font=font_hex)
            x += box_size + spacing
        img.save(filepath, "JPEG", quality=95, dpi=(300, 300))


    # ====================== Save All Palettes ======================
    def save_all_palettes_as_jpg(self, instance):
        if not HAS_PIL:
            self.show_message("PIL (Pillow) tidak terinstal. Install dengan 'pip install Pillow'")
            return
        if not self.palettes:
            self.show_message("Tidak ada palet untuk disimpan.")
            return

        folder_name = "Pallet Color Ramp"
        save_folder = None

        if platform == 'android':
            try:
                from android.storage import primary_external_storage_path
                base = primary_external_storage_path()
                if base:
                    pics = os.path.join(base, 'Pictures', folder_name)
                    if not os.path.exists(pics):
                        try:
                            os.makedirs(pics, exist_ok=True)
                            save_folder = pics
                        except:
                            down = os.path.join(base, 'Download', folder_name)
                            if not os.path.exists(down):
                                try:
                                    os.makedirs(down, exist_ok=True)
                                    save_folder = down
                                except:
                                    save_folder = os.path.join(os.getcwd(), folder_name)
                            else:
                                save_folder = down
                    else:
                        save_folder = pics
                else:
                    raise Exception("No external storage")
            except:
                ext = os.environ.get('EXTERNAL_STORAGE', '/storage/emulated/0')
                pics = os.path.join(ext, 'Pictures', folder_name)
                if not os.path.exists(pics):
                    try:
                        os.makedirs(pics, exist_ok=True)
                        save_folder = pics
                    except:
                        down = os.path.join(ext, 'Download', folder_name)
                        if not os.path.exists(down):
                            try:
                                os.makedirs(down, exist_ok=True)
                                save_folder = down
                            except:
                                save_folder = os.path.join(os.getcwd(), folder_name)
                        else:
                            save_folder = down
                else:
                    save_folder = pics
        else:
            try:
                from plyer import filechooser
                filechooser.choose_dir(on_selection=self._save_palettes_to_path)
                return
            except:
                try:
                    import tkinter as tk
                    from tkinter import filedialog
                    root = tk.Tk()
                    root.withdraw()
                    folder = filedialog.askdirectory(title="Pilih folder untuk menyimpan gambar palet")
                    root.destroy()
                    if folder:
                        target = os.path.join(folder, folder_name)
                        if not os.path.exists(target):
                            os.makedirs(target, exist_ok=True)
                        self._save_palettes_to_path([target])
                    else:
                        self.show_message("Penyimpanan dibatalkan.")
                    return
                except:
                    folder = os.getcwd()
                    target = os.path.join(folder, folder_name)
                    if not os.path.exists(target):
                        os.makedirs(target, exist_ok=True)
                    self._save_palettes_to_path([target])
                    self.show_message(f"Tidak dapat membuka dialog folder. Disimpan di:\n{target}")
                    return

        if save_folder:
            if not os.path.exists(save_folder):
                try:
                    os.makedirs(save_folder, exist_ok=True)
                except:
                    save_folder = os.path.join(os.getcwd(), folder_name)
                    os.makedirs(save_folder, exist_ok=True)
            self._save_palettes_to_path([save_folder])
        else:
            fallback = os.path.join(os.getcwd(), folder_name)
            if not os.path.exists(fallback):
                os.makedirs(fallback, exist_ok=True)
            self._save_palettes_to_path([fallback])

    def _save_palettes_to_path(self, selected_paths):
        if not selected_paths:
            return
        folder = selected_paths[0]
        if not os.path.exists(folder):
            try:
                os.makedirs(folder, exist_ok=True)
            except:
                folder = os.getcwd()
        filename = f"all_palettes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(folder, filename)
        try:
            self._generate_all_palettes_image(filepath)
            self.show_message(f"✅ Semua palet berhasil disimpan di:\n{filepath}")
        except Exception as e:
            self.show_message(f"❌ Gagal menyimpan: {str(e)}")

    def _generate_all_palettes_image(self, filepath):
        valid_palettes = [p for p in self.palettes if p['colors']]
        if not valid_palettes:
            raise Exception("Tidak ada palet dengan warna.")

        width = 2400
        scale = width / 900
        box_size = int(110 * scale)
        title_font_size = int(box_size * 0.34)
        hex_font_size = int(box_size * 0.24)
        margin = int(30 * scale)
        spacing = int(14 * scale)
        cols = 6
        per_row_height = box_size + hex_font_size + 14

        total_height = margin
        for palet in valid_palettes:
            colors = palet['colors']
            rows = (len(colors) - 1) // cols + 1
            total_height += title_font_size + 20
            total_height += rows * (per_row_height + spacing)
            total_height += margin
        total_height += margin

        img = PILImage.new('RGB', (width, total_height), color=(255,255,255))
        draw = ImageDraw.Draw(img)
        font_title = self._get_font(title_font_size)
        font_hex = self._get_font(hex_font_size)

        y = margin
        for palet in valid_palettes:
            draw.text((margin, y), palet['name'], fill=(0,0,0), font=font_title)
            y += title_font_size + 20
            colors = palet['colors']
            x = margin
            for i, (r, g, b) in enumerate(colors):
                if i > 0 and i % cols == 0:
                    y += per_row_height + spacing
                    x = margin
                draw.rectangle([x, y, x+box_size, y+box_size], fill=(r,g,b), outline=(0,0,0), width=2)
                hex_text = "#{:02X}{:02X}{:02X}".format(r, g, b)
                draw.text((x, y + box_size + 6), hex_text, fill=(0,0,0), font=font_hex)
                x += box_size + spacing
            y += per_row_height + spacing + margin
        img.save(filepath, "JPEG", quality=95, dpi=(300, 300))

    def show_message(self, text):
        popup = Popup(title="Info", content=Label(text=text, font_size=18), size_hint=(0.7, 0.4))
        popup.open()


# ======================== Halaman 3: Color Detector =========================




# ==================== Desain Menu Tab (flat, gaya gambar 3) ====================
# Teks polos rata (tanpa ikon/kotak). Tab tidak aktif: hitam, normal.
# Tab aktif: ungu, bold, dengan garis bawah tipis.
TAB_ACTIVE_COLOR = get_color_from_hex('#5A31D6')
TAB_INACTIVE_COLOR = (0.13, 0.13, 0.13, 1)


def _style_flat_tab(tab):
    """Buat satu TabbedPanelItem tampil flat: tanpa kotak/atlas bawaan Kivy,
    teks polos, dan garis bawah ungu saat tab tersebut aktif."""
    tab.background_normal = ''
    tab.background_down = ''
    tab.background_color = (1, 1, 1, 1)
    tab.color = TAB_INACTIVE_COLOR
    tab.bold = False
    tab.font_size = dp(13)
    tab.halign = 'center'
    tab.valign = 'middle'
    tab.shorten = True
    tab.shorten_from = 'right'

    def _update_text_size(*_args):
        # Batasi lebar teks ke lebar tab supaya tidak numpuk ke tab sebelah,
        # dan otomatis dipangkas (...) kalau tetap kepanjangan.
        tab.text_size = (max(tab.width - dp(8), dp(10)), tab.height)

    with tab.canvas.after:
        underline_color = Color(*TAB_ACTIVE_COLOR)
        underline_color.a = 0
        underline = Line(width=dp(1.6))

    def _refresh(*_args):
        is_active = (tab.state == 'down')
        underline_color.a = 1 if is_active else 0
        tab.color = TAB_ACTIVE_COLOR if is_active else TAB_INACTIVE_COLOR
        tab.bold = is_active
        y = tab.y + dp(2)
        underline.points = [tab.x + dp(10), y, tab.right - dp(10), y]

    tab.bind(state=_refresh, pos=_refresh, size=_refresh)
    tab.bind(size=_update_text_size)
    _update_text_size()
    _refresh()


# ======================== Aplikasi Utama =========================
class ColorFinderApp(App):
    def build(self):
        self.title = "Color Picker Pro"
        tab_panel = TabbedPanel(
            do_default_tab=False,
            tab_width=Window.width / 4.0,
            tab_height=dp(56),
            background_color=(1, 1, 1, 1),
            background_image='',
            border=(0, 0, 0, 0),
        )
        tab1 = TabbedPanelItem(text="Color Picker")
        self.main_content = MainContent()
        tab1.content = self.main_content
        tab_panel.add_widget(tab1)
        self.color_gear_tab = ColorGearTab()
        tab_panel.add_widget(self.color_gear_tab)
        tab3 = ColorDetectorTab()
        tab_panel.add_widget(tab3)
        tab4 = ColorMagnifierTab()
        tab_panel.add_widget(tab4)

        # Terapkan desain flat (gaya gambar 3) ke keempat tab secara seragam
        for _t in (tab1, self.color_gear_tab, tab3, tab4):
            _style_flat_tab(_t)

        # Window.width saat build() dipanggil kadang belum akurat di Android
        # (belum full-size). Hitung ulang lebar tab sesudah frame pertama,
        # dan setiap kali ukuran window berubah (misal rotasi layar).
        def _resync_tab_width(*_args):
            tab_panel.tab_width = Window.width / 4.0
        Clock.schedule_once(_resync_tab_width, 0)
        Window.bind(width=_resync_tab_width, height=_resync_tab_width)

        # Beri tahu Halaman 1 (Color Picker) di mana tab bar berada,
        # supaya tombol "Export Tampilan Penuh" bisa ikut menyertakan
        # baris tab (Color Picker | Color Gear | ...) di paling atas.
        # Nama atribut internal ini bisa beda-beda tergantung versi
        # Kivy, jadi dicoba beberapa kemungkinan; kalau tidak ada satu
        # pun yang cocok, tab bar cukup dilewati (bagian lain tetap
        # ter-export normal).
        tab_strip = None
        for attr_name in ('_tab_strip', 'tab_strip', '_tab_layout'):
            tab_strip = getattr(tab_panel, attr_name, None)
            if tab_strip is not None:
                break
        self.main_content.tab_strip_widget = tab_strip

        # Garis tipis abu-abu di bawah baris menu tab (gaya gambar 3)
        if tab_strip is not None:
            with tab_strip.canvas.after:
                Color(0.85, 0.85, 0.85, 1)
                strip_border = Line(width=dp(1))

            def _refresh_strip_border(*_args):
                strip_border.points = [tab_strip.x, tab_strip.y, tab_strip.right, tab_strip.y]

            tab_strip.bind(pos=_refresh_strip_border, size=_refresh_strip_border)
            _refresh_strip_border()

        return tab_panel

    def _save_all_progress(self):
        # Simpan kerjaan Halaman 1 (Color Picker) & Halaman 2 (Color Gear/Palet)
        try:
            if hasattr(self, 'main_content'):
                self.main_content.force_save()
        except Exception:
            pass
        try:
            if hasattr(self, 'color_gear_tab'):
                self.color_gear_tab.force_save()
        except Exception:
            pass

    def on_pause(self):
        # Dipanggil Android saat app diminimize/di-background
        self._save_all_progress()
        return True

    def on_resume(self):
        pass

    def on_stop(self):
        # Dipanggil saat aplikasi benar-benar ditutup
        self._save_all_progress()


if __name__ == '__main__':
    try:
        request_storage_permissions()
    except Exception:
        pass
    ColorFinderApp().run()