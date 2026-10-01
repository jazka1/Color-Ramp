# color_detector.py
# ============================================================
# Halaman 3: Color Detector
# Fitur: Deteksi 20 warna dominan dari gambar,
#        tampilkan plate color + nama + arti,
#        analisis kata kunci dari arti warna,
#        rekomendasi color grading dengan random sampling.
# ============================================================

# color_detector.py - Final
# Halaman 3: Deteksi warna, plate color, analisis color grading
# Font plate color 28, background putih, popup analisis besar

import os
import io
import random
import re
import threading
from collections import Counter
import math

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.utils import platform

# ==================== Komponen UI flat (gaya referensi) ====================
# Disalin ringan di sini (bukan import dari main.py) supaya tidak ada
# circular import antara main.py <-> color_detector.py.
ACCENT_PURPLE = get_color_from_hex('#5A31D6')


class FlatButton(ButtonBehavior, Label):
    """Tombol datar bersudut bulat (pengganti Button bawaan Kivy)."""
    def __init__(self, bg_rgba=(1, 1, 1, 1), border_rgba=(0.8, 0.8, 0.85, 1),
                 radius=None, **kwargs):
        kwargs.setdefault('halign', 'center')
        kwargs.setdefault('valign', 'middle')
        super().__init__(**kwargs)
        self.bind(size=lambda *_a: setattr(self, 'text_size', self.size))
        self.bg_rgba = bg_rgba
        self.border_rgba = border_rgba
        self.radius = [radius if radius is not None else dp(12)]
        with self.canvas.before:
            self._border_color = Color(*self.border_rgba)
            self._border_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=self.radius)
            self._bg_color = Color(*self.bg_rgba)
            self._bg_rect = RoundedRectangle(
                pos=(self.x + dp(1.5), self.y + dp(1.5)),
                size=(self.width - dp(3), self.height - dp(3)),
                radius=self.radius)
        self.bind(pos=self._update_bg, size=self._update_bg)
        self.bind(disabled=self._update_disabled_look)

    def _update_disabled_look(self, *_args):
        self.opacity = 0.45 if self.disabled else 1

    def _update_bg(self, *_args):
        self._border_rect.pos = self.pos
        self._border_rect.size = self.size
        self._bg_rect.pos = (self.x + dp(1.5), self.y + dp(1.5))
        self._bg_rect.size = (self.width - dp(3), self.height - dp(3))


def add_rounded_card(widget, bg_rgba=(0.93, 0.93, 0.95, 1), radius=dp(14)):
    """Tempel latar kartu bulat di belakang sebuah widget (mengikuti pos/size-nya)."""
    with widget.canvas.before:
        Color(*bg_rgba)
        rect = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius])

    def _update(*_args):
        rect.pos = widget.pos
        rect.size = widget.size

    widget.bind(pos=_update, size=_update)
    return rect


class ButtonBehaviorTile(ButtonBehavior, BoxLayout):
    """BoxLayout biasa yang bisa disentuh -- dipakai untuk bungkus
    thumbnail folder/gambar di browser file "Pilih Gambar"."""
    pass


from kivy.core.image import Image as CoreImage

# ===== Cek PIL =====
try:
    from PIL import Image as PILImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ===== DAFTAR WARNA & ARTI =====
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

# ===== FUNGSI KONVERSI =====
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

# ===== DETEKSI DOMINAN =====
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

# ===== ANALISIS =====
def analyze_color_meanings(colors):
    meanings = []
    for (r, g, b) in colors:
        hex_code = "#{:02X}{:02X}{:02X}".format(r, g, b)
        name = find_nearest_color_name(hex_code)
        meaning = get_color_meaning(name)
        if meaning:
            meanings.append(meaning)
    
    if not meanings:
        return {
            'top_keywords': [],
            'kesimpulan': "Tidak ada arti warna yang tersedia.",
            'recommended_grading': "Tidak dapat menentukan",
            'confidence': 0
        }
    
    all_words = []
    stopwords = {'dan', 'di', 'ke', 'dari', 'yang', 'untuk', 'dengan', 'pada', 'ini', 'itu', 'tersebut', 'juga', 'serta', 'oleh', 'karena', 'sebagai', 'dalam', 'atas', 'akan', 'telah', 'adalah', 'atau', 'salah', 'lain', 'lebih', 'sangat', 'cukup', 'terlalu', 'begitu', 'demikian', 'begini', 'seperti', 'antara', 'bagi', 'baik', 'buruk', 'besar', 'kecil', 'banyak', 'sedikit', 'semua', 'setiap', 'mana', 'apa', 'siapa', 'kenapa', 'bagaimana', 'kapan', 'dimana'}
    
    for meaning in meanings:
        words = re.findall(r'\b[a-z]+\b', meaning.lower())
        for w in words:
            if len(w) > 2 and w not in stopwords:
                all_words.append(w)
    
    if not all_words:
        return {
            'top_keywords': [],
            'kesimpulan': "Tidak ada kata kunci signifikan ditemukan.",
            'recommended_grading': "Tidak dapat menentukan",
            'confidence': 0
        }
    
    word_freq = Counter(all_words)
    top_keywords = [word for word, count in word_freq.most_common(5)]
    
    confidence = 0
    if len(colors) >= 10:
        sample_scores = []
        for _ in range(5):
            sample = random.sample(colors, min(5, len(colors)))
            sample_meanings = []
            for (r, g, b) in sample:
                hex_code = "#{:02X}{:02X}{:02X}".format(r, g, b)
                name = find_nearest_color_name(hex_code)
                meaning = get_color_meaning(name)
                if meaning:
                    sample_meanings.append(meaning)
            sample_words = []
            for meaning in sample_meanings:
                words = re.findall(r'\b[a-z]+\b', meaning.lower())
                sample_words.extend([w for w in words if len(w) > 2 and w not in stopwords])
            if sample_words:
                sample_freq = Counter(sample_words)
                sample_top = [w for w, c in sample_freq.most_common(3)]
                match = sum(1 for kw in top_keywords if kw in sample_top)
                sample_scores.append(match / min(3, len(sample_top)) if sample_top else 0)
        if sample_scores:
            confidence = (sum(sample_scores) / len(sample_scores)) * 100
        else:
            confidence = 50
    else:
        confidence = 60
    
    grading_map = {
        'Teal and Orange (The Blockbuster Look)': ['teal', 'orange', 'kontras', 'dinamis', 'blockbuster', 'hangat', 'dingin', 'energi', 'gairah', 'keberanian', 'kreativitas', 'kesuksesan'],
        'Bleach Bypass (Silver Retention)': ['metalik', 'misteri', 'keras', 'retensi', 'perak', 'gelap', 'kekuatan', 'elegan', 'misterius', 'otoritas', 'kemewahan'],
        'Vintage / Nostalgic': ['kenangan', 'lama', 'hangat', 'lembut', 'retro', 'nostalgia', 'klasik', 'kelembutan', 'kenyamanan', 'tradisi'],
        'Dark and Moody': ['gelap', 'misterius', 'dramatis', 'intens', 'suram', 'mendalam', 'kekuatan', 'elegan', 'misteri', 'ketenangan'],
        'Cross Processing (X-Pro)': ['eksperimental', 'vibrant', 'kontras', 'berani', 'kreatif', 'warna', 'energi', 'gairah', 'kebebasan', 'individualitas'],
        'Monochromatic / Single-Tone': ['monokrom', 'seragam', 'moody', 'sederhana', 'elegan', 'netral', 'keseimbangan', 'kedamaian', 'stabilitas']
    }
    
    scores = {}
    for grading, keywords in grading_map.items():
        score = sum(1 for kw in top_keywords if kw in keywords)
        scores[grading] = score
    
    if scores:
        best_grading = max(scores, key=scores.get)
        if scores[best_grading] == 0:
            best_grading = "Teal and Orange (The Blockbuster Look) - default"
    else:
        best_grading = "Tidak dapat ditentukan"
    
    if top_keywords:
        keywords_str = ", ".join(top_keywords[:5])
        kesimpulan = f"Berdasarkan analisis 20 warna dominan, gambar ini memiliki karakteristik: {keywords_str}."
    else:
        kesimpulan = "Tidak ada kata kunci dominan yang teridentifikasi."
    
    return {
        'top_keywords': top_keywords,
        'kesimpulan': kesimpulan,
        'recommended_grading': best_grading,
        'confidence': round(confidence, 1)
    }

# ===== KELAS ColorDetectorTab =====
class ColorDetectorTab(TabbedPanelItem):
    def __init__(self, **kwargs):
        super().__init__(text="Color Detector", **kwargs)
        self.analysis_result = None
        self.popup_bg = None

        # Seluruh halaman di-scroll jadi satu, latar abu muda (gaya referensi)
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, bar_width=dp(6))
        with scroll.canvas.before:
            Color(0.933, 0.933, 0.945, 1)
            self._bg_rect = Rectangle(pos=scroll.pos, size=scroll.size)
        scroll.bind(pos=self._update_scroll_bg, size=self._update_scroll_bg)
        self.content = scroll

        body = BoxLayout(orientation='vertical', size_hint_y=None,
                          padding=dp(16), spacing=dp(14))
        body.bind(minimum_height=body.setter('height'))
        scroll.add_widget(body)

        # --- Baris: "Pilih Gambar" (putih, rounded) + tombol kamera (ungu) ---
        pilih_row = BoxLayout(size_hint=(1, None), height=dp(100), spacing=dp(10))
        btn_select = FlatButton(text="Pilih Gambar", font_size=40, bold=False,
                                 color=(0.1, 0.1, 0.1, 1),
                                 bg_rgba=(1, 1, 1, 1), border_rgba=(0.8, 0.8, 0.85, 1))
        btn_select.bind(on_release=self.select_image)
        btn_camera = FlatButton(text="\U0001F4F7", font_size=38,
                                 color=(1, 1, 1, 1),
                                 bg_rgba=ACCENT_PURPLE, border_rgba=ACCENT_PURPLE,
                                 size_hint=(None, None), size=(dp(100), dp(100)))
        btn_camera.bind(on_release=self.select_image)
        pilih_row.add_widget(btn_select)
        pilih_row.add_widget(btn_camera)
        body.add_widget(pilih_row)

        # --- Widget gambar (sudut membulat) ---
        image_wrap = BoxLayout(size_hint=(1, None), height=dp(340), padding=dp(4))
        add_rounded_card(image_wrap, bg_rgba=(1, 1, 1, 1), radius=dp(14))
        self.image_widget = KivyImage(size_hint=(1, 1), keep_ratio=True, allow_stretch=True)
        image_wrap.add_widget(self.image_widget)
        body.add_widget(image_wrap)

        # --- Tombol Deteksi 20 Warna (abu muda, rounded, tanpa ikon) ---
        btn_detect = FlatButton(text="Deteksi 20 Warna", font_size=42, bold=False,
                                 color=(0.1, 0.1, 0.1, 1),
                                 bg_rgba=(0.93, 0.93, 0.95, 1), border_rgba=(0.85, 0.85, 0.88, 1),
                                 size_hint=(1, None), height=dp(100))
        btn_detect.bind(on_release=self.detect_colors)
        body.add_widget(btn_detect)

        # --- Tombol Lihat Analisis (sama gayanya, disabled di awal) ---
        self.btn_analysis = FlatButton(text="Lihat Analisis", font_size=42, bold=False,
                                        color=(0.1, 0.1, 0.1, 1),
                                        bg_rgba=(0.93, 0.93, 0.95, 1), border_rgba=(0.85, 0.85, 0.88, 1),
                                        size_hint=(1, None), height=dp(100), disabled=True)
        self.btn_analysis.bind(on_release=self.show_analysis_popup)
        body.add_widget(self.btn_analysis)

        # --- Daftar hasil warna -- ikut scroll bersama body ---
        self.result_grid = GridLayout(cols=1, spacing=dp(14), size_hint=(1, None))
        self.result_grid.bind(minimum_height=self.result_grid.setter('height'))
        body.add_widget(self.result_grid)
        self.result_scroll = scroll  # alias, dipakai kode lama bila ada referensi

        # Label ringkasan kecil
        self.summary_label = Label(
            text="",
            font_size=40,
            color=(0.2, 0.2, 0.2, 1),
            size_hint=(1, None),
            height=dp(130),
            halign='left',
            valign='top',
        )
        self.summary_label.bind(size=lambda *_a: setattr(
            self.summary_label, 'text_size', (self.summary_label.width, None)))
        body.add_widget(self.summary_label)

    def _update_scroll_bg(self, *_args):
        self._bg_rect.pos = self.content.pos
        self._bg_rect.size = self.content.size

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
        """Browser gambar buatan sendiri (bukan plyer/FileChooserIconView
        bawaan Kivy) -- menampilkan THUMBNAIL ASLI 240px langsung di
        grid (sama seperti di halaman Color Magnifier), jadi tidak perlu
        panel "Preview" terpisah lagi dan tidak ada risiko crash plyer."""
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

        def make_tile(label_text, thumb_source, on_press):
            tile = BoxLayout(orientation='vertical', size_hint=(1, None), height=dp(150), spacing=dp(4))
            btn = ButtonBehaviorTile(on_press=on_press)
            if thumb_source:
                # Thumbnail 240px dibuat di BACKGROUND THREAD (PIL) lewat
                # _load_texture_async yang sudah ada -- bukan file
                # resolusi asli, jadi cepat & tidak freeze.
                img = KivyImage(size_hint=(1, 1), allow_stretch=True, keep_ratio=True)
                btn.add_widget(img)

                def on_ready(texture, w=img):
                    w.texture = texture

                self._load_texture_async(thumb_source, max_size=240, on_ready=on_ready)
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

            # Batasi jumlah thumbnail sekaligus -- folder kamera bisa
            # berisi ratusan foto.
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

    def _load_texture_async(self, filepath, max_size, on_ready, on_error=None):
        """
        Decode & resize gambar di BACKGROUND THREAD (bukan di UI thread),
        supaya UI tidak freeze/lag saat memuat foto beresolusi besar dari
        kamera (misalnya 4000x3000px). Texture Kivy sendiri baru dibuat di
        main thread lewat Clock.schedule_once (wajib, karena texture perlu
        konteks OpenGL).
        """
        def _finish_ready(texture):
            Clock.schedule_once(lambda dt: on_ready(texture), 0)

        def _finish_error(err):
            if on_error:
                Clock.schedule_once(lambda dt: on_error(err), 0)

        def _worker():
            try:
                if HAS_PIL:
                    img = PILImage.open(filepath)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    if img.width > max_size or img.height > max_size:
                        img.thumbnail((max_size, max_size), PILImage.Resampling.LANCZOS)
                    buf = io.BytesIO()
                    img.save(buf, format='PNG')
                    png_bytes = buf.getvalue()

                    def _apply(dt):
                        try:
                            core_img = CoreImage(io.BytesIO(png_bytes), ext='png')
                            on_ready(core_img.texture)
                        except Exception as e:
                            if on_error:
                                on_error(str(e))
                    Clock.schedule_once(_apply, 0)
                else:
                    # Tanpa PIL, tidak bisa di-downscale di background,
                    # jadi langsung decode via CoreImage (masih lebih ringan
                    # daripada Image.source karena tanpa cache Loader).
                    def _apply_direct(dt):
                        try:
                            core_img = CoreImage(filepath)
                            on_ready(core_img.texture)
                        except Exception as e:
                            if on_error:
                                on_error(str(e))
                    Clock.schedule_once(_apply_direct, 0)
            except Exception as e:
                _finish_error(str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def load_image(self, filepath):
        if not os.path.exists(filepath):
            self.summary_label.text = "❌ File tidak ditemukan."
            return
        self.summary_label.text = "⏳ Memuat gambar..."

        def on_ready(texture):
            self.image_widget.texture = texture
            self.summary_label.text = f"✅ Gambar dimuat: {os.path.basename(filepath)}"

        def on_error(err):
            self.summary_label.text = (
                f"❌ Gagal memuat gambar: {err}. "
                f"Pastikan file adalah gambar yang valid (jpg, png, dll) dan tidak korup."
            )

        # max_size 1280 cukup untuk tampilan preview & sampling deteksi warna,
        # jauh lebih ringan daripada memuat foto kamera resolusi penuh.
        self._load_texture_async(filepath, max_size=1280, on_ready=on_ready, on_error=on_error)

    def detect_colors(self, instance):
        if not self.image_widget.texture:
            self.summary_label.text = "❌ Silakan pilih gambar terlebih dahulu."
            return
        colors = get_dominant_colors(self.image_widget.texture, num_colors=20, sample_size=3000)
        if not colors:
            self.summary_label.text = "❌ Gagal mendeteksi warna."
            return

        # Tampilkan plate color: kartu bulat abu muda + swatch bulat + teks
        self.result_grid.clear_widgets()
        for (r,g,b) in colors:
            hex_code = "#{:02X}{:02X}{:02X}".format(r, g, b)
            name = find_nearest_color_name(hex_code)
            meaning = get_color_meaning(name)
            box = BoxLayout(size_hint_y=None, height=dp(150), spacing=dp(16), padding=[dp(10), dp(10)])
            add_rounded_card(box, bg_rgba=(0.93, 0.93, 0.95, 1), radius=dp(14))

            # Preview warna (kotak bulat, tinggi -- gaya referensi)
            preview = BoxLayout(size_hint_x=None, width=dp(110))
            with preview.canvas:
                Color(r/255.0, g/255.0, b/255.0, 1)
                preview_rect = RoundedRectangle(pos=preview.pos, size=preview.size, radius=[dp(10)])
            preview.bind(pos=self._update_preview_rect(preview_rect, preview),
                         size=self._update_preview_rect(preview_rect, preview))
            box.add_widget(preview)

            # Informasi: "#HEX • Nama • arti" (boleh melipat 2 baris)
            info = Label(
                text=f"{hex_code}  \u2022  {name}  \u2022  {meaning}",
                font_size=38,
                color=(0.1, 0.1, 0.1, 1),
                halign='left',
                valign='middle',
                size_hint_x=1,
            )
            info.bind(size=lambda l, *_a: setattr(l, 'text_size', (l.width, None)))
            box.add_widget(info)
            self.result_grid.add_widget(box)

        # Analisis
        analysis = analyze_color_meanings(colors)
        self.analysis_result = analysis
        self.btn_analysis.disabled = False
        self.btn_analysis.text = "Lihat Analisis"
        summary = (
            f"🔍 Kata kunci: {', '.join(analysis['top_keywords'][:5])} | "
            f"🎯 Rekomendasi: {analysis['recommended_grading']} | "
            f"⚡ Keyakinan: {analysis['confidence']}%"
        )
        self.summary_label.text = summary
        print("DEBUG: Analisis selesai, tombol aktif.")

    def show_analysis_popup(self, instance):
        if not self.analysis_result:
            return
        a = self.analysis_result
        # Konten popup dengan background putih
        content = BoxLayout(orientation='vertical', padding=25, spacing=20)
        with content.canvas.before:
            Color(1, 1, 1, 1)
            self.popup_bg = Rectangle(pos=content.pos, size=content.size)
        content.bind(pos=self._update_popup_bg, size=self._update_popup_bg)

        # Judul font besar
        title = Label(text="📊 Analisis Color Grading", font_size=48, bold=True, color=(0,0,0,1), size_hint=(1, 0.08))
        content.add_widget(title)

        # Scroll untuk isi
        scroll = ScrollView(size_hint=(1, 0.82))
        text_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=15)
        text_box.bind(minimum_height=text_box.setter('height'))

        # Isi dengan font besar (36) dan wrap otomatis
        lines = [
            f"🔍 Kata kunci dominan: {', '.join(a['top_keywords'][:5])}",
            f"📝 Kesimpulan: {a['kesimpulan']}",
            f"🎯 Rekomendasi grading: **{a['recommended_grading']}**",
            f"⚡ Keyakinan: {a['confidence']}%"
        ]
        for line in lines:
            lbl = Label(
                text=line,
                font_size=36,
                color=(0,0,0,1),
                halign='left',
                valign='top',
                size_hint_y=None,
                text_size=(None, None)
            )
            def bind_label(l):
                l.text_size = (l.width, None)
                l.height = max(50, l.texture_size[1] + 10)
            lbl.bind(size=lambda l, *args: bind_label(l))
            Clock.schedule_once(lambda dt, l=lbl: bind_label(l), 0.1)
            text_box.add_widget(lbl)

        scroll.add_widget(text_box)
        content.add_widget(scroll)

        # Tombol tutup font besar
        btn_close = Button(text="Tutup", size_hint=(1, 0.1), font_size=42,
                           background_color=(0.2,0.6,0.9,1), color=(1,1,1,1))
        popup = Popup(title="", content=content, size_hint=(0.9, 0.9), auto_dismiss=False)
        btn_close.bind(on_press=popup.dismiss)
        content.add_widget(btn_close)
        popup.open()

    def _update_popup_bg(self, instance, value):
        if self.popup_bg:
            self.popup_bg.pos = instance.pos
            self.popup_bg.size = instance.size

    def _update_item_bg(self, instance, value):
        # Fungsi untuk update background item
        for child in instance.canvas.before.children:
            if isinstance(child, Rectangle):
                child.pos = instance.pos
                child.size = instance.size
                break

    def _update_preview_rect(self, rect, widget):
        def callback(instance, value):
            rect.pos = widget.pos
            rect.size = widget.size
        return callback