"""Métricas y contornos del mismo OTF incluido, sin fuentes del sistema."""
from functools import lru_cache

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

from ..config import FONT_DIR, Blocked


@lru_cache
def font(weight=400):
    name = "Bold" if weight >= 700 else "SemiBold" if weight >= 600 else "Regular"
    return TTFont(FONT_DIR / f"Inter-{name}.otf")


def glyphs(text, weight=400):
    f = font(weight)
    cmap, glyphset = f.getBestCmap(), f.getGlyphSet()
    for char in text:
        name = cmap.get(ord(char))
        if name is None:
            raise Blocked(f"Glifo no disponible en Inter: {char!r}")
        yield name, glyphset[name], f["hmtx"][name][0]


def width(text, size, weight=400):
    return sum(advance for _, _, advance in glyphs(text, weight)) * size / font(weight)["head"].unitsPerEm


def wrap(text, size, max_width, weight=400):
    lines, current = [], ""
    for word in text.split(" "):
        candidate = current + " " + word if current else word
        if width(candidate, size, weight) > max_width:
            if not current or width(word, size, weight) > max_width:
                raise Blocked("Una palabra no cabe en la caja")
            lines.append(current)
            current = word
        else:
            current = candidate
    return lines + [current]


def outlines(text, x, y, size, weight=400):
    scale = size / font(weight)["head"].unitsPerEm
    result = []
    for _, glyph, advance in glyphs(text, weight):
        pen = SVGPathPen(font(weight).getGlyphSet())
        glyph.draw(pen)
        path = pen.getCommands()
        if path:
            result.append(f'<path d="{path}" transform="translate({x:.6f} {y:.6f}) scale({scale:.9f} {-scale:.9f})"/>')
        x += advance * scale
    return "".join(result)
