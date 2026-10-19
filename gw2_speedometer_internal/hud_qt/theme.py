"""Tema visual del HUD: colores, tipografía (Montserrat), escala y opacidad."""

import glob
import os

from PySide6.QtGui import QColor, QFont, QFontDatabase

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(HERE)

_FAMILY = None


def load_fonts():
    """Registra Montserrat (fuentes del repo y, si existe, la variable del sistema).

    Devuelve la familia elegida. Llamar después de crear la QApplication.
    """
    global _FAMILY
    if _FAMILY:
        return _FAMILY
    patterns = [os.path.join(HERE, "fonts", "*.ttf"),
                os.path.join(APP_DIR, "fonts", "Montserrat*.ttf"),
                "/usr/share/fonts/**/Montserrat-VariableFont_wght.ttf",
                os.path.expanduser("~/.local/share/fonts/**/Montserrat*.ttf"),
                os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts", "Montserrat*.ttf")]
    for pat in patterns:
        for f in glob.glob(pat, recursive=True):
            QFontDatabase.addApplicationFont(f)
    fams = set(QFontDatabase.families())
    for cand in ("Montserrat", "Montserrat Regular", "Inter", "Noto Sans", "DejaVu Sans"):
        if cand in fams:
            _FAMILY = cand
            break
    else:
        _FAMILY = QFont().defaultFamily()
    return _FAMILY


class Theme:
    # Paleta (estilo HUD racing oscuro)
    TEXT = QColor(238, 243, 250)
    TEXT_DIM = QColor(150, 162, 182)
    TEXT_MUTED = QColor(95, 106, 126)
    ACCENT = QColor(0, 212, 255)        # cian: jugador / elementos activos
    GREEN = QColor(46, 230, 124)
    ORANGE = QColor(255, 158, 44)
    RED = QColor(255, 66, 82)
    GOLD = QColor(255, 204, 64)
    PURPLE = QColor(176, 120, 255)
    PANEL_TOP = QColor(24, 30, 44)
    PANEL_BOTTOM = QColor(9, 12, 20)

    def __init__(self, scale=1.0, opacity=1.0, bg_alpha=0.66, compact=False):
        self.scale = scale          # 1.0 = 1080p, 2.0 ~ 4K
        self.opacity = opacity      # opacidad global del contenido (0-1)
        self.bg_alpha = bg_alpha    # translucidez del fondo de los paneles (0-1)
        self.compact = compact
        self.family = load_fonts()

    def px(self, v):
        return v * self.scale

    def font(self, px, weight=600, spacing=0.0, tnum=False, italic=False):
        f = QFont(self.family)
        f.setPixelSize(max(1, round(px * self.scale)))
        f.setWeight(QFont.Weight(int(weight)))
        f.setItalic(italic)
        f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        f.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        if spacing:
            f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing * self.scale)
        if tnum and hasattr(QFont, "Tag"):  # dígitos tabulares (Qt >= 6.7): el crono no "baila"
            f.setFeature(QFont.Tag("tnum"), 1)
        return f

    @staticmethod
    def speed_color(v):
        """Verde hasta 99 (boost beetle), naranja hasta 120, rojo por encima."""
        if v <= 92:
            return QColor(Theme.GREEN)
        if v <= 99:
            return lerp_color(Theme.GREEN, QColor(200, 230, 60), (v - 92) / 7)
        if v <= 120:
            return lerp_color(QColor(255, 196, 50), Theme.ORANGE, (v - 99) / 21)
        return lerp_color(Theme.ORANGE, Theme.RED, min(1.0, (v - 120) / 6))

    @staticmethod
    def delta_color(d):
        if d is None:
            return QColor(Theme.TEXT_DIM)
        return QColor(Theme.GREEN) if d < 0 else QColor(Theme.RED) if d > 0 else QColor(Theme.TEXT)


def lerp_color(a, b, t):
    t = max(0.0, min(1.0, t))
    return QColor(int(a.red() + (b.red() - a.red()) * t),
                  int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t),
                  int(a.alpha() + (b.alpha() - a.alpha()) * t))


def with_alpha(c, a):
    c = QColor(c)
    c.setAlpha(max(0, min(255, int(a))))
    return c
