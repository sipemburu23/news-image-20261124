#!/usr/bin/env python3
"""news-image edisi 24 — "The World in One Day — Tuesday 24 November 2026".
Draws entry.png (1024x1024) with PIL. Written from scratch for this edition.
Design: bagarte-style compact masthead, 3 leads + 10 cards + 13 briefs = 26 stories,
7 region segments, UTC timeline, day-in-numbers box, solid world map, DATE CHECK.
Density rules (ed-24): briefs 8-10, decks 1 line, brief 15px, deck 13px, lead 32px+,
card 24px+, dense rows (text <16px) <= 80 measured. Scenes are drawn DIRECTLY into
their art boxes (no intermediate canvas, no cover-crop) so no scene text can be
clipped by a crop edge — the ed-23 "239/5" -> "9/5" failure mode cannot happen here.
Sole fact source: ../news-image-20261124-research.md (see brief file).
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1024, 1024

# ---- palette (cream paper, dark ink, navy) ----
PAPER = (245, 240, 230)
INK = (28, 23, 16)
INK_SOFT = (74, 66, 54)
GREY = (120, 112, 96)
NAVY = (24, 38, 58)
NAVY_BOX = (22, 36, 56)
NAVY_LT = (217, 226, 236)
RED = (140, 29, 24)
GOLD = (184, 138, 47)
GREEN = (40, 120, 60)
BLUE = (34, 64, 120)
ORANGE = (180, 60, 20)
WHITE = (252, 250, 245)
SEA = (168, 196, 214)
LAND = (96, 112, 94)
LAND_LINE = (210, 200, 170)

DJ = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
DJB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
DJI = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"
PF = os.path.join(HERE, "fonts", "PlayfairDisplay.ttf")

_font_cache = {}


def font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def sans(size):
    return font(DJ, size)


def sans_b(size):
    return font(DJB, size)


def sans_i(size):
    return font(DJI, size)


def playfair(size):
    return font(PF, size)


def text_w(text, f):
    return f.getlength(text)


def wrap(text, f, width, max_lines=None):
    """Greedy word wrap. Returns list of lines (asserts max_lines if given)."""
    words = text.split(" ")
    lines, cur = [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if f.getlength(trial) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    if max_lines is not None:
        assert len(lines) <= max_lines, f"wrap overflow: {lines} (max {max_lines})"
    return lines


# ---- dense-row recorder: every <16px text line registers its y band ----
DENSE_BANDS = []  # list of (y0, y1)


def note_dense(y0, y1):
    DENSE_BANDS.append((y0, y1))


def dense_row_count():
    """Count distinct y bands (merge bands overlapping or within 2px)."""
    bands = sorted(DENSE_BANDS)
    merged = []
    for a, b in bands:
        if merged and a <= merged[-1][1] + 2:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return len(merged), merged


TAG_COL = {"CONFIRMED": (40, 120, 60), "OFFICIAL": (34, 64, 120),
           "REPORTED": (180, 60, 20), "FORECAST": (120, 90, 20)}

# ---- layout constants ----
MX = 10
CW = 1004
LEAD_W = 250
NUM_W = 224
LEAD_ART_H = 86
CARD_ART_H = 72
CARD_W = 194
CARD_GAP = 8

TOP_H = 16
MAST_Y = 0            # draw y for the masthead text (ink lands ~y=22)
MAST_SIZE, MAST_TRACK, MAST_STROKE = 82, 1.0, 3
REGION_Y, REGION_H = 98, 18
UTC_Y, UTC_H = 124, 36
LEAD_Y, LEAD_H = 168, 206
CARD_ROWS_Y = (382, 562)
CARD_H = 180
BRIEF_Y, BRIEF_H = 750, 140
DC_Y, DC_H = 898, 76
FOOT_Y, FOOT_H = 984, 28

# ---- content (from research; headlines/decks trimmed to measured fits) ----
LEADS = [
    # num, headline, deck, label, tag, scene
    (1, "Huawei guilty on 10 counts", "Brooklyn jury convicts on 10 of 12.",
     "BROOKLYN \u00b7 GLOBAL \u00b7 COURT", "CONFIRMED", "court"),
    (2, "Iran claims Hormuz hit", "IRGC claims a ship hit; unconfirmed.",
     "HORMUZ \u00b7 MIDDLE EAST \u00b7 WAR", "REPORTED", "hormuz"),
    (3, "Kyiv owns Baltic hit", "Admits Sat. strike; defends Libya.",
     "GULF OF FINLAND \u00b7 EUROPE \u00b7 WAR", "CONFIRMED", "sparta"),
]

CARDS = [
    # v4: 10 cards in 2 rows of 5. Nepal (old 7), Haftar (old 13) and
    # Congo (old 15) moved to briefs 14-16; the rest renumbered.
    (4, "Riyadh tower hit again", "Eleven hurt in second strike.",
     "RIYADH \u00b7 MIDDLE EAST \u00b7 WAR", "CONFIRMED", "riyadh"),
    (5, "AFCON crown restored", "CAS overturns title strip.",
     "DAKAR \u00b7 AFRICA \u00b7 SPORT", "OFFICIAL", "senegal"),
    (6, "Sanofi buys Insmed", "$41bn drug buy of 2026.",
     "PARIS \u00b7 EUROPE \u00b7 BUSINESS", "OFFICIAL", "sanofi"),
    (7, "Meningitis alert in Gaza", "272 cases in October.",
     "GAZA \u00b7 MIDDLE EAST \u00b7 HEALTH", "OFFICIAL", "gaza"),
    (8, "Hanoi blast kills six", "Gas leak flattens restaurant.",
     "HANOI \u00b7 ASIA \u00b7 DISASTER", "CONFIRMED", "hanoi"),
    (9, "Turkish chopper down", "Five killed in second crash.",
     "ESKISEHIR \u00b7 EUROPE \u00b7 AVIATION", "CONFIRMED", "chopper"),
    (10, "Cartagena siege", "Gunmen hold 30; 5 freed.",
     "CARTAGENA \u00b7 S. AMERICA \u00b7 CRIME", "CONFIRMED", "cartagena"),
    (11, "US drone tracked Isidro", "Mexico to try him at home.",
     "GUASAVE \u00b7 AMERICAS \u00b7 CRIME", "CONFIRMED", "drone"),
    (12, "Russian jets off Ulleungdo", "Seoul scrambles F-15K jets.",
     "ULLEUNGDO \u00b7 ASIA \u00b7 DEFENCE", "CONFIRMED", "jets"),
    (13, "Houthis 60 km from Aden", "Army digs in near capital.",
     "ADEN \u00b7 MIDDLE EAST \u00b7 WAR", "CONFIRMED", "aden"),
]

BRIEFS = [
    # num, tag, text — v4: 13 briefs (2 cols 7+6). 14-16 are the former
    # cards Nepal, Haftar, Congo; 17-26 are the v1-v3 briefs, unchanged.
    (14, "CONFIRMED", "M5.6 quake rattles Nepal."),
    (15, "CONFIRMED", "Haftar makes first trip to Ankara."),
    (16, "REPORTED", "Rebels claim Congo plane hit Sunday."),
    (17, "OFFICIAL", "UK sanctions Houthis and four officials."),
    (18, "CONFIRMED", "Car bomb wounds 25 in Villavicencio."),
    (19, "CONFIRMED", "Hamas security chief killed in Gaza."),
    (20, "REPORTED", "Monday's Lahj bus toll rises to 25."),
    (21, "CONFIRMED", "Baghdad orders Kurdish oil takeover."),
    (22, "CONFIRMED", "Malaysia sends 6,803 Myanmar home."),
    (23, "CONFIRMED", "Euclid finds most distant quasar yet."),
    (24, "OFFICIAL", "UN: 47,000 women killed by partners."),
    (25, "CONFIRMED", "Australia: sue tech, fines to 5%."),
    (26, "CONFIRMED", "England level T20 in Gold Coast."),
]

NUMBERS = [
    # value, label, source (source printed under every value)
    ("$41bn", "Sanofi buys Insmed", "Sanofi"),
    ("10/12", "Huawei guilty counts", "Reuters"),
    ("+3.91%", "Nikkei, Tuesday close", "Reuters"),
    ("60 km", "Houthis from Aden", "Reuters"),
    ("272", "Gaza meningitis, Oct", "Gaza Health Ministry"),
    ("47,000", "women killed by partners", "UNODC / UN Women"),
]

REGIONS = [("GLOBAL", 3), ("MIDDLE EAST", 7), ("EUROPE", 4), ("ASIA", 4),
           ("AFRICA", 3), ("AMERICAS", 3), ("OCEANIA", 2)]

UTC_POINTS = [("01:00", "Hanoi blast"), ("01:32", "Nepal quake"),
              ("04:14", "Ulleungdo jets"), ("10:10", "Gaza alert"),
              ("12:03", "UK sanctions"), ("14:27", "Riyadh tower"),
              ("20:41", "Huawei verdict")]

DATE_CHECK = (
    "Every story on this page is Tuesday 24 November 2026's news. "
    "Not Tuesday: ICJ Myanmar ruling (Thu); Nvidia +31.48%, COP31, EU 22nd "
    "sanctions, Women's WC 2035, Megaspeed, Treasury sanctions and NHS "
    "EDITH (all Mon); Rutte on NATO space, Pentagon Canada rebuke, 'Ma' death "
    "sentence and FDA Welgemda (all Mon); Bukele on Haiti (Fri 20 Nov); "
    "Dymer toll. Not yet: Shenzhou-24 Wed "
    "25 Nov; Huawei sentenced 14 Sep 2027; Hasina plans return 16 Dec; Erdogan to "
    "Libya 8\u20139 Dec.")

FOOTER = [
    "CONFIRMED = two or more independent sources \u00b7 OFFICIAL = announced by an "
    "institution \u00b7 REPORTED = a single-source claim, not yet confirmed",
    "Scenes are drawn illustrations, not photos \u00b7 Sources: Reuters \u00b7 AP \u00b7 BBC "
    "\u00b7 CNN \u00b7 WSJ \u00b7 Bloomberg \u00b7 ESA \u00b7 UNODC \u00b7 Sanofi \u00b7 CAS",
]

# map pins: number -> (lon, lat)
# v4: 13 pins (leads 1-3 + cards 4-13). Nepal, Ankara and Minembwe are
# briefs now and carry no pin.
PINS = {
    1: (-73.99, 40.70), 2: (56.25, 26.57), 3: (26.90, 59.90),
    4: (46.64, 24.76), 5: (-17.45, 14.69), 6: (2.35, 48.85),
    7: (34.47, 31.50), 8: (105.82, 21.01), 9: (30.52, 39.78),
    10: (-75.51, 10.39), 11: (-108.47, 25.57), 12: (130.87, 37.49),
    13: (45.03, 12.79),
}


def draw_tracked(d, text, size, track, stroke, x0, y, fill=INK):
    """Draw text with per-character tracking and a stroke; returns advance."""
    f = playfair(size)
    x = x0
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill, stroke_width=stroke,
               stroke_fill=fill)
        x += f.getlength(ch) * track
    return x - x0


def sky(d, box, top, bottom):
    """Vertical gradient sky inside box (inclusive)."""
    x0, y0, x1, y1 = box
    h = max(1, y1 - y0)
    for i in range(h):
        t = i / h
        c = tuple(int(top[k] + (bottom[k] - top[k]) * t) for k in range(3))
        d.line([(x0, y0 + i), (x1, y0 + i)], fill=c)


def sun(d, cx, cy, r, col=(250, 214, 110)):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    d.ellipse([cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3],
              outline=(250, 230, 150), width=2)


def cloud(d, x, y, s, col=(252, 252, 250)):
    d.ellipse([x, y, x + int(22 * s), y + int(9 * s)], fill=col)
    d.ellipse([x + int(5 * s), y - int(4 * s), x + int(20 * s), y + int(6 * s)],
              fill=col)
    d.ellipse([x + int(14 * s), y, x + int(30 * s), y + int(8 * s)], fill=col)


def ground(d, box, col=(96, 72, 48)):
    x0, y0, x1, y1 = box
    d.rectangle([x0, y1 - 4, x1, y1], fill=col)


# ---- scenes: every scene draws DIRECTLY into its art box (x0,y0,x1,y1) ----
# No intermediate canvas and no cover-crop, so no text or shape can be clipped
# by a crop edge. In-scene text is kept to one centred word at most, >=8px
# from every edge of the box.

def scene_court(d, box):
    # Brooklyn federal courthouse, bright day, red GUILTY stamp.
    sky(d, box, (150, 198, 232), (234, 230, 224))
    x0, y0, x1, y1 = box
    sun(d, x1 - 24, y0 + 12, 8)
    cloud(d, x0 + 12, y0 + 10, 0.9)
    d.rectangle([x0 + 18, y0 + 34, x0 + 118, y1 - 4], fill=(210, 205, 190))
    d.polygon([(x0 + 18, y0 + 34), (x0 + 68, y0 + 16), (x0 + 118, y0 + 34)],
              fill=(180, 172, 152))
    for cx in range(x0 + 26, x0 + 112, 18):
        d.rectangle([cx, y0 + 40, cx + 9, y1 - 10], fill=(240, 236, 224))
    d.rectangle([x0 + 58, y0 + 52, x0 + 78, y1 - 10], fill=(60, 50, 44))
    # gavel, right
    d.rectangle([x0 + 150, y0 + 44, x0 + 196, y0 + 56], fill=(110, 72, 40))
    d.rectangle([x0 + 168, y0 + 56, x0 + 178, y0 + 76], fill=(90, 58, 32))
    d.rectangle([x0 + 146, y0 + 74, x0 + 200, y0 + 80], fill=(140, 100, 60))
    # GUILTY stamp, centred, clear of edges
    f = sans_b(20)
    t = "GUILTY"
    tw = f.getlength(t)
    cx = (x0 + x1) / 2 - tw / 2
    cy = y0 + 8
    d.rectangle([cx - 6, cy - 3, cx + tw + 6, cy + 22], outline=RED, width=3)
    d.text((cx, cy), t, font=f, fill=RED)
    ground(d, box)


def scene_hormuz(d, box):
    # Strait of Hormuz: blue sea, cliffs, container ship + tanker, mines.
    sky(d, box, (150, 198, 232), (210, 224, 236))
    x0, y0, x1, y1 = box
    sun(d, x1 - 24, y0 + 12, 8)
    d.rectangle([x0, y0 + 46, x1, y1], fill=(52, 96, 140))
    for wy in range(y0 + 54, y1 - 4, 10):
        d.line([(x0 + 6, wy), (x1 - 6, wy)], fill=(80, 130, 175), width=1)
    # cliffs
    d.polygon([(x0, y0 + 46), (x0 + 34, y0 + 8), (x0 + 52, y0 + 46)],
              fill=(150, 130, 100))
    d.polygon([(x1, y0 + 46), (x1 - 30, y0 + 14), (x1 - 48, y0 + 46)],
              fill=(140, 122, 94))
    # container ship
    d.rectangle([x0 + 62, y0 + 52, x0 + 150, y0 + 68], fill=(40, 44, 52))
    for i, c in enumerate(((200, 70, 50), (40, 90, 160), (220, 180, 60))):
        d.rectangle([x0 + 68 + i * 26, y0 + 40, x0 + 90 + i * 26, y0 + 52],
                    fill=c)
    d.rectangle([x0 + 146, y0 + 42, x0 + 156, y0 + 52], fill=(240, 240, 238))
    # tanker, right
    d.rectangle([x0 + 168, y0 + 56, x0 + 226, y0 + 70], fill=(120, 40, 36))
    d.rectangle([x0 + 210, y0 + 46, x0 + 220, y0 + 56], fill=(240, 240, 238))
    # mines (small spiked dots, well inside the box)
    for mx, my in ((x0 + 96, y0 + 74), (x0 + 190, y0 + 76), (x0 + 132, y0 + 78)):
        d.ellipse([mx - 4, my - 4, mx + 4, my + 4], fill=(24, 28, 32))
        d.line([(mx - 7, my), (mx + 7, my)], fill=(24, 28, 32), width=1)
        d.line([(mx, my - 7), (mx, my + 7)], fill=(24, 28, 32), width=1)
    ground(d, box, (52, 96, 140))


def scene_sparta(d, box):
    # Burning cargo ship in the Gulf of Finland, drones above.
    sky(d, box, (150, 198, 232), (228, 222, 208))
    x0, y0, x1, y1 = box
    sun(d, x1 - 24, y0 + 12, 8)
    cloud(d, x0 + 16, y0 + 10, 0.9)
    d.rectangle([x0, y0 + 48, x1, y1], fill=(70, 110, 150))
    for wy in range(y0 + 56, y1 - 4, 10):
        d.line([(x0 + 6, wy), (x1 - 6, wy)], fill=(100, 140, 180), width=1)
    # hull
    d.rectangle([x0 + 40, y0 + 52, x0 + 190, y0 + 70], fill=(60, 62, 66))
    d.rectangle([x0 + 52, y0 + 38, x0 + 120, y0 + 52], fill=(180, 60, 40))
    d.rectangle([x0 + 128, y0 + 42, x0 + 176, y0 + 52], fill=(200, 180, 60))
    # flames + smoke
    for fx, fh in ((x0 + 70, 18), (x0 + 96, 24), (x0 + 124, 16), (x0 + 150, 20)):
        d.polygon([(fx - 10, y0 + 40), (fx, y0 + 40 - fh), (fx + 10, y0 + 40)],
                  fill=(230, 120, 30))
        d.polygon([(fx - 5, y0 + 40), (fx, y0 + 40 - fh + 8), (fx + 5, y0 + 40)],
                  fill=(250, 200, 60))
    d.ellipse([x0 + 88, y0 + 8, x0 + 118, y0 + 26], fill=(90, 86, 82))
    d.ellipse([x0 + 108, y0 + 2, x0 + 138, y0 + 20], fill=(110, 106, 102))
    # two sea drones
    for dx, dy in ((x0 + 196, y0 + 16), (x0 + 214, y0 + 30)):
        d.ellipse([dx - 8, dy - 3, dx + 8, dy + 3], fill=(24, 28, 32))
        d.line([(dx - 12, dy - 5), (dx + 12, dy - 5)], fill=(24, 28, 32), width=1)
    ground(d, box, (70, 110, 150))


def scene_riyadh(d, box):
    # PIF Tower, Riyadh: tall glass tower, smoke plume, city below.
    sky(d, box, (150, 198, 232), (236, 228, 210))
    x0, y0, x1, y1 = box
    sun(d, x1 - 24, y0 + 12, 8)
    cloud(d, x0 + 10, y0 + 12, 0.8)
    # city blocks
    for bx, bh, bw in ((x0 + 8, 26, 24), (x0 + 40, 34, 24), (x0 + 150, 30, 24), (x0 + 176, 22, 18)):
        d.rectangle([bx, y1 - 4 - bh, bx + bw, y1 - 4], fill=(170, 162, 140))
    # tower
    d.rectangle([x0 + 82, y0 + 6, x0 + 128, y1 - 4], fill=(52, 84, 122))
    d.rectangle([x0 + 82, y0 + 6, x0 + 128, y0 + 14], fill=(30, 55, 90))
    for wy in range(y0 + 20, y1 - 10, 9):
        for wx in (x0 + 88, x0 + 104, x0 + 118):
            d.rectangle([wx, wy, wx + 8, wy + 5], fill=(190, 210, 230))
    # smoke from the top
    d.ellipse([x0 + 96, y0 + 2, x0 + 122, y0 + 12], fill=(120, 116, 110))
    d.ellipse([x0 + 88, y0 + 2, x0 + 110, y0 + 16], fill=(140, 136, 130))
    d.ellipse([x0 + 132, y0 + 18, x0 + 152, y0 + 32], fill=(90, 86, 82))
    ground(d, box)


def scene_senegal(d, box):
    # AFCON trophy on a green pitch, Senegal colours at the base.
    sky(d, box, (150, 198, 232), (220, 232, 210))
    x0, y0, x1, y1 = box
    sun(d, x1 - 24, y0 + 12, 8)
    d.rectangle([x0, y0 + 44, x1, y1 - 4], fill=(60, 140, 70))
    for lx in range(x0, x1, 24):
        d.line([(min(max(lx, x0 + 4), x1 - 4), y0 + 44), (min(lx + 12, x1 - 4), y1 - 4)], fill=(70, 155, 80), width=6)
    # trophy, centred
    d.polygon([(x0 + 84, y0 + 14), (x0 + 110, y0 + 14), (x0 + 104, y0 + 34),
               (x0 + 90, y0 + 34)], fill=(220, 180, 60))
    d.ellipse([x0 + 78, y0 + 12, x0 + 90, y0 + 26], outline=(220, 180, 60),
              width=3)
    d.ellipse([x0 + 104, y0 + 12, x0 + 116, y0 + 26], outline=(220, 180, 60),
              width=3)
    d.rectangle([x0 + 92, y0 + 34, x0 + 102, y0 + 42], fill=(200, 160, 50))
    d.rectangle([x0 + 82, y0 + 42, x0 + 112, y0 + 48], fill=(200, 160, 50))
    # football
    d.ellipse([x0 + 138, y1 - 26, x0 + 162, y1 - 4], fill=(250, 250, 248))
    d.polygon([(x0 + 146, y1 - 20), (x0 + 154, y1 - 20), (x0 + 156, y1 - 12),
               (x0 + 150, y1 - 8), (x0 + 144, y1 - 12)], fill=(30, 30, 30))
    # Senegal stripe
    d.rectangle([x0, y1 - 12, x0 + 64, y1 - 4], fill=(0, 122, 60))
    d.rectangle([x0 + 64, y1 - 12, x0 + 128, y1 - 4], fill=(240, 210, 40))
    d.rectangle([x0 + 128, y1 - 12, x1, y1 - 4], fill=(200, 40, 40))
    ground(d, box, (60, 140, 70))


def scene_sanofi(d, box):
    # Pill bottle and coins on a light bench.
    sky(d, box, (228, 232, 238), (240, 234, 218))
    x0, y0, x1, y1 = box
    for ty in (y0 + 14, y0 + 26, y0 + 40):
        d.line([(x0 + 10, ty), (x1 - 10, ty)], fill=(180, 190, 200), width=1)
    # bottle
    d.rectangle([x0 + 66, y0 + 12, x0 + 118, y0 + 20], fill=(40, 90, 160))
    d.rectangle([x0 + 58, y0 + 20, x0 + 126, y1 - 8], fill=(250, 250, 248),
                outline=(120, 110, 96))
    # Blue label band confined to the bottle body (ends y1-8, inside the
    # 50px art box). No text on the bottle: the old "INS"/"MED" label spilled
    # past the art box and overlapped the headline (audit B1). The headline
    # already says "Insmed".
    d.rectangle([x0 + 58, y0 + 34, x0 + 126, y1 - 8], fill=(40, 90, 160))
    # coins with $
    for cx, cy in ((x0 + 148, y1 - 20), (x0 + 168, y1 - 16), (x0 + 158, y1 - 28)):
        d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=(220, 180, 60),
                  outline=(180, 140, 40), width=2)
        d.text((cx - 4, cy - 7), "$", font=sans_b(11), fill=(120, 90, 20))
    # capsules
    d.ellipse([x0 + 20, y1 - 18, x0 + 44, y1 - 8], fill=(200, 60, 50))
    d.ellipse([x0 + 32, y1 - 18, x0 + 44, y1 - 8], fill=(250, 250, 248))
    ground(d, box)


def scene_nepal(d, box):
    # Snow-capped Himalaya + red seismograph trace.
    sky(d, box, (150, 198, 232), (232, 236, 240))
    x0, y0, x1, y1 = box
    sun(d, x1 - 24, y0 + 12, 8)
    cloud(d, x0 + 12, y0 + 10, 0.9)
    d.polygon([(x0, y1 - 4), (x0 + 48, y0 + 14), (x0 + 96, y1 - 4)],
              fill=(120, 130, 150))
    d.polygon([(x0 + 40, y1 - 4), (x0 + 96, y0 + 6), (x0 + 152, y1 - 4)],
              fill=(90, 100, 125))
    d.polygon([(x0 + 88, y0 + 6), (x0 + 96, y0 + 16), (x0 + 104, y0 + 6)],
              fill=(250, 250, 248))
    d.polygon([(x0 + 40, y0 + 14), (x0 + 48, y0 + 22), (x0 + 56, y0 + 14)],
              fill=(240, 240, 238))
    d.polygon([(x0 + 140, y1 - 4), (x0 + 172, y0 + 22), (x0 + 194, y1 - 4)],
              fill=(140, 148, 165))
    # seismograph trace across the lower sky
    pts = [(x0 + 10 + i * 8, y0 + 34 + (0 if i % 3 else -8 if i % 2 else 8))
           for i in range(22)]
    d.line(pts, fill=RED, width=2)
    ground(d, box)


def scene_gaza(d, box):
    # Hospital with teal roof and red cross, daylight.
    sky(d, box, (150, 198, 232), (234, 230, 224))
    x0, y0, x1, y1 = box
    sun(d, x1 - 24, y0 + 12, 8)
    d.rectangle([x0 + 16, y0 + 22, x0 + 120, y1 - 4], fill=(240, 240, 238))
    d.rectangle([x0 + 16, y0 + 22, x0 + 120, y0 + 30], fill=(40, 110, 140))
    for wy in range(y0 + 36, y1 - 10, 11):
        for wx in range(x0 + 24, x0 + 112, 15):
            d.rectangle([wx, wy, wx + 8, wy + 6], fill=(150, 190, 210))
    d.rectangle([x0 + 58, y0 + 29, x0 + 78, y0 + 49], fill=WHITE)
    d.rectangle([x0 + 65, y0 + 32, x0 + 71, y0 + 46], fill=(200, 40, 40))
    d.rectangle([x0 + 61, y0 + 36, x0 + 75, y0 + 42], fill=(200, 40, 40))
    # ambulance, right
    d.rectangle([x0 + 138, y0 + 34, x0 + 182, y0 + 48], fill=(250, 250, 248),
                outline=(120, 110, 96))
    d.rectangle([x0 + 138, y0 + 34, x0 + 182, y0 + 40], fill=(200, 40, 40))
    d.ellipse([x0 + 146, y0 + 41, x0 + 154, y0 + 49], fill=(30, 30, 30))
    d.ellipse([x0 + 168, y0 + 41, x0 + 176, y0 + 49], fill=(30, 30, 30))
    ground(d, box)


def scene_hanoi(d, box):
    # Hotpot restaurant, flames and smoke, daylight street.
    sky(d, box, (150, 198, 232), (236, 228, 210))
    x0, y0, x1, y1 = box
    sun(d, x1 - 24, y0 + 12, 8)
    d.rectangle([x0 + 20, y0 + 18, x0 + 130, y1 - 4], fill=(196, 150, 90))
    d.rectangle([x0 + 20, y0 + 18, x0 + 130, y0 + 26], fill=(150, 60, 48))
    for wy in range(y0 + 32, y1 - 10, 11):
        for wx in range(x0 + 28, x0 + 122, 18):
            d.rectangle([wx, wy, wx + 10, wy + 7], fill=(230, 210, 170))
    # flames from the roof
    for fx, fh in ((x0 + 52, 14), (x0 + 76, 20), (x0 + 100, 13)):
        d.polygon([(fx - 9, y0 + 20), (fx, y0 + 20 - fh), (fx + 9, y0 + 20)],
                  fill=(230, 120, 30))
    d.ellipse([x0 + 62, y0 + 2, x0 + 88, y0 + 14], fill=(110, 106, 102))
    d.ellipse([x0 + 84, y0 + 2, x0 + 108, y0 + 10], fill=(130, 126, 122))
    # street lantern
    d.ellipse([x0 + 158, y0 + 20, x0 + 176, y0 + 38], fill=(200, 40, 40))
    d.rectangle([x0 + 165, y0 + 38, x0 + 169, y1 - 4], fill=(60, 50, 44))
    ground(d, box)


def scene_chopper(d, box):
    # AS-532 Cougar in flight over hills, daylight.
    sky(d, box, (150, 198, 232), (232, 236, 240))
    x0, y0, x1, y1 = box
    sun(d, x1 - 24, y0 + 12, 8)
    cloud(d, x0 + 12, y0 + 10, 0.9)
    d.polygon([(x0, y1 - 4), (x0 + 50, y0 + 34), (x0 + 110, y1 - 4)],
              fill=(110, 130, 100))
    d.polygon([(x0 + 90, y1 - 4), (x0 + 150, y0 + 28), (x1, y1 - 4)],
              fill=(90, 110, 85))
    # helicopter body
    d.ellipse([x0 + 62, y0 + 16, x0 + 128, y0 + 34], fill=(90, 100, 90))
    d.rectangle([x0 + 122, y0 + 22, x0 + 168, y0 + 28], fill=(80, 90, 80))
    d.rectangle([x0 + 162, y0 + 14, x0 + 168, y0 + 36], fill=(70, 80, 70))
    d.line([(x0 + 48, y0 + 12), (x0 + 142, y0 + 12)], fill=(40, 44, 40),
           width=3)
    d.line([(x0 + 88, y0 + 8), (x0 + 102, y0 + 8)], fill=(40, 44, 40), width=2)
    d.ellipse([x0 + 66, y0 + 20, x0 + 82, y0 + 30], fill=(180, 210, 230))
    # rotor wash lines
    for lx in (x0 + 70, x0 + 96, x0 + 122):
        d.line([(lx, y0 + 38), (lx, y0 + 44)], fill=(180, 190, 200), width=1)
    ground(d, box)


def scene_cartagena(d, box):
    # Supermarket block, police car, palm tree.
    sky(d, box, (150, 198, 232), (236, 228, 210))
    x0, y0, x1, y1 = box
    sun(d, x1 - 24, y0 + 12, 8)
    d.rectangle([x0 + 14, y0 + 16, x0 + 140, y1 - 4], fill=(220, 210, 180))
    d.rectangle([x0 + 14, y0 + 16, x0 + 140, y0 + 26], fill=(40, 90, 160))
    for wx in range(x0 + 22, x0 + 134, 16):
        d.rectangle([wx, y0 + 32, wx + 10, y1 - 12], fill=(150, 190, 210))
    d.rectangle([x0 + 60, y0 + 34, x0 + 94, y1 - 4], fill=(60, 60, 64))
    # police car
    d.rectangle([x0 + 148, y0 + 34, x0 + 188, y0 + 46], fill=(250, 250, 248),
                outline=(40, 60, 120))
    d.rectangle([x0 + 148, y0 + 34, x0 + 188, y0 + 39], fill=(40, 60, 120))
    d.ellipse([x0 + 154, y0 + 44, x0 + 162, y0 + 52], fill=(30, 30, 30))
    d.ellipse([x0 + 174, y0 + 44, x0 + 182, y0 + 52], fill=(30, 30, 30))
    # palm
    d.rectangle([x0 + 176, y0 + 8, x0 + 180, y0 + 30], fill=(110, 80, 50))
    for a in (-40, -15, 10, 35):
        ex = x0 + 178 + int(14 * math.cos(math.radians(a - 90)))
        ey = max(y0 + 2, y0 + 8 + int(10 * math.sin(math.radians(a - 90))))
        d.line([(x0 + 178, y0 + 8), (ex, ey)], fill=(60, 140, 70), width=3)
    ground(d, box)


def scene_drone(d, box):
    # Surveillance drone over Sinaloa desert mountains.
    sky(d, box, (150, 198, 232), (238, 226, 200))
    x0, y0, x1, y1 = box
    sun(d, x1 - 24, y0 + 12, 8)
    cloud(d, x0 + 14, y0 + 10, 0.9)
    d.polygon([(x0, y1 - 4), (x0 + 46, y0 + 30), (x0 + 100, y1 - 4)],
              fill=(170, 130, 90))
    d.polygon([(x0 + 80, y1 - 4), (x0 + 140, y0 + 24), (x1, y1 - 4)],
              fill=(150, 112, 76))
    # road
    d.polygon([(x0 + 84, y1 - 4), (x0 + 100, y1 - 4), (x0 + 118, y0 + 40),
               (x0 + 106, y0 + 40)], fill=(90, 80, 70))
    # quadcopter drone, centred high
    cx, cy = x0 + 97, y0 + 18
    d.rectangle([cx - 14, cy - 3, cx + 14, cy + 3], fill=(40, 44, 48))
    d.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(24, 28, 32))
    for sx in (-20, 20):
        d.ellipse([cx + sx - 7, cy - 8, cx + sx + 7, cy - 2], fill=(120, 130, 140))
        d.line([(cx + sx - 10, cy - 5), (cx + sx + 10, cy - 5)],
               fill=(90, 100, 110), width=2)
    d.line([(cx, cy + 3), (cx, cy + 12)], fill=(40, 44, 48), width=2)
    d.ellipse([cx - 3, cy + 12, cx + 3, cy + 18], fill=(24, 28, 32))
    ground(d, box)


def scene_haftar(d, box):
    # Two flags over Ankara: Turkish crescent + Libyan tricolour.
    sky(d, box, (150, 198, 232), (236, 228, 210))
    x0, y0, x1, y1 = box
    sun(d, x1 - 24, y0 + 12, 8)
    # building
    d.rectangle([x0 + 60, y0 + 30, x0 + 134, y1 - 4], fill=(200, 192, 168))
    d.polygon([(x0 + 60, y0 + 30), (x0 + 97, y0 + 16), (x0 + 134, y0 + 30)],
              fill=(170, 162, 140))
    for wx in range(x0 + 68, x0 + 128, 14):
        d.rectangle([wx, y0 + 38, wx + 7, y0 + 48], fill=(120, 140, 170))
    # Turkish flag, left pole
    d.rectangle([x0 + 22, y0 + 10, x0 + 26, y1 - 4], fill=(60, 50, 44))
    d.rectangle([x0 + 26, y0 + 10, x0 + 66, y0 + 30], fill=(200, 40, 40))
    d.ellipse([x0 + 34, y0 + 14, x0 + 48, y0 + 26], fill=(250, 250, 248))
    d.ellipse([x0 + 38, y0 + 16, x0 + 48, y0 + 24], fill=(200, 40, 40))
    # Libyan flag, right pole
    d.rectangle([x0 + 168, y0 + 10, x0 + 172, y1 - 4], fill=(60, 50, 44))
    d.rectangle([x0 + 140, y0 + 10, x0 + 172, y0 + 30], fill=(200, 40, 40))
    d.rectangle([x0 + 140, y0 + 16, x0 + 172, y0 + 24], fill=(30, 30, 30))
    d.rectangle([x0 + 140, y0 + 24, x0 + 172, y0 + 30], fill=(0, 122, 60))
    ground(d, box)


def scene_jets(d, box):
    # Two jets over Ulleungdo island, sea below.
    sky(d, box, (150, 198, 232), (228, 224, 212))
    x0, y0, x1, y1 = box
    sun(d, x1 - 24, y0 + 12, 8)
    d.rectangle([x0, y0 + 40, x1, y1], fill=(70, 110, 150))
    for wy in range(y0 + 48, y1 - 4, 9):
        d.line([(x0 + 6, wy), (x1 - 6, wy)], fill=(100, 140, 180), width=1)
    # island
    d.polygon([(x0 + 60, y1 - 4), (x0 + 96, y0 + 30), (x0 + 136, y1 - 4)],
              fill=(70, 130, 80))
    d.ellipse([x0 + 88, y0 + 30, x0 + 104, y0 + 42], fill=(90, 150, 100))
    # jets
    for jx, jy in ((x0 + 130, y0 + 14), (x0 + 156, y0 + 26)):
        d.polygon([(jx, jy), (jx + 22, jy + 5), (jx, jy + 10)],
                  fill=(120, 125, 135))
        d.polygon([(jx + 6, jy + 2), (jx + 14, jy - 4), (jx + 16, jy + 2)],
                  fill=(100, 105, 115))
        d.line([(jx - 12, jy + 5), (jx, jy + 5)], fill=(220, 220, 220), width=2)
    ground(d, box, (70, 110, 150))


def scene_congo(d, box):
    # Cessna over jungle, dashed search path.
    sky(d, box, (150, 198, 232), (222, 234, 214))
    x0, y0, x1, y1 = box
    sun(d, x1 - 24, y0 + 12, 8)
    # jungle canopy
    for tx, tr in ((x0 + 16, 14), (x0 + 44, 18), (x0 + 76, 13), (x0 + 104, 17),
                   (x0 + 136, 14), (x0 + 164, 18)):
        d.ellipse([tx, y1 - 30, tx + tr * 2, y1 - 4], fill=(60, 130, 70))
    d.rectangle([x0, y1 - 8, x1, y1 - 4], fill=(40, 100, 55))
    # small plane
    d.ellipse([x0 + 70, y0 + 16, x0 + 124, y0 + 28], fill=(240, 240, 238),
              outline=(90, 90, 90))
    d.rectangle([x0 + 116, y0 + 18, x0 + 138, y0 + 24], fill=(200, 200, 200),
                outline=(90, 90, 90))
    d.line([(x0 + 88, y0 + 10), (x0 + 106, y0 + 10)], fill=(60, 60, 60),
           width=2)
    d.ellipse([x0 + 72, y0 + 19, x0 + 84, y0 + 25], fill=(150, 190, 210))
    # dashed search path
    for i in range(8):
        sx = x0 + 20 + i * 20
        d.line([(sx, y0 + 40), (sx + 10, y0 + 40)], fill=RED, width=2)
    ground(d, box, (40, 100, 55))


def scene_aden(d, box):
    # Desert, defensive line and mountains near Aden.
    sky(d, box, (150, 198, 232), (240, 228, 200))
    x0, y0, x1, y1 = box
    sun(d, x1 - 24, y0 + 12, 8)
    d.polygon([(x0, y1 - 4), (x0 + 50, y0 + 26), (x0 + 110, y1 - 4)],
              fill=(170, 140, 100))
    d.polygon([(x0 + 100, y1 - 4), (x0 + 150, y0 + 30), (x1, y1 - 4)],
              fill=(150, 122, 86))
    d.rectangle([x0, y0 + 40, x1, y1 - 4], fill=(210, 180, 130))
    # defensive line: sandbags + vehicles
    for bx in range(x0 + 16, x1 - 20, 26):
        d.ellipse([bx, y1 - 22, bx + 18, y1 - 12], fill=(190, 165, 115),
                  outline=(140, 118, 80))
    d.rectangle([x0 + 130, y1 - 30, x0 + 168, y1 - 18], fill=(90, 95, 70))
    d.ellipse([x0 + 136, y1 - 18, x0 + 144, y1 - 10], fill=(30, 30, 30))
    d.ellipse([x0 + 154, y1 - 18, x0 + 162, y1 - 10], fill=(30, 30, 30))
    d.rectangle([x0 + 146, y1 - 36, x0 + 152, y1 - 30], fill=(70, 75, 55))
    ground(d, box)


SCENES = {
    "court": scene_court, "hormuz": scene_hormuz, "sparta": scene_sparta,
    "riyadh": scene_riyadh, "senegal": scene_senegal, "sanofi": scene_sanofi,
    "nepal": scene_nepal, "gaza": scene_gaza, "hanoi": scene_hanoi,
    "chopper": scene_chopper, "cartagena": scene_cartagena,
    "drone": scene_drone, "haftar": scene_haftar, "jets": scene_jets,
    "congo": scene_congo, "aden": scene_aden,
}


# ---- world map: my own simplified equirectangular outlines ----
# lon -175..185 -> x ; lat 75..-55 -> y (map box passed in)
def _lonlat(lon, lat, box):
    x0, y0, x1, y1 = box
    x = x0 + (lon + 175) / 360.0 * (x1 - x0)
    y = y0 + (75 - lat) / 130.0 * (y1 - y0)
    return (x, y)


LANDMASSES = {
    "north_america": [(-168, 66), (-140, 70), (-115, 72), (-95, 69),
                      (-80, 66), (-70, 60), (-60, 52), (-55, 47),
                      (-70, 44), (-76, 35), (-81, 26), (-90, 21),
                      (-95, 16), (-85, 11), (-80, 8), (-88, 14),
                      (-97, 18), (-106, 22), (-114, 29), (-122, 37),
                      (-124, 46), (-132, 56), (-152, 60), (-165, 60)],
    "greenland": [(-55, 64), (-40, 62), (-30, 68), (-22, 72), (-35, 78),
                  (-58, 78), (-66, 72)],
    "south_america": [(-79, 9), (-70, 12), (-62, 10), (-54, 6), (-50, 0),
                      (-42, -4), (-35, -8), (-40, -20), (-48, -28),
                      (-58, -38), (-66, -46), (-70, -54), (-74, -42),
                      (-73, -28), (-70, -18), (-77, -12), (-81, -4),
                      (-80, 3)],
    "africa": [(-17, 15), (-15, 22), (-9, 31), (0, 36), (11, 37),
               (21, 32), (31, 31), (35, 28), (40, 20), (44, 12),
               (51, 11), (47, 1), (40, -6), (39, -16), (35, -26),
               (28, -33), (19, -35), (15, -27), (12, -17), (13, -9),
               (9, 0), (9, 4), (-8, 4), (-14, 9)],
    "eurasia": [(-10, 36), (-9, 43), (-2, 48), (-4, 50), (2, 51),
                (7, 54), (10, 59), (18, 56), (22, 56), (27, 60),
                (30, 63), (35, 69), (50, 69), (68, 72), (85, 75),
                (105, 75), (125, 72), (145, 70), (165, 67), (178, 65),
                (168, 60), (158, 52), (143, 49), (140, 39), (134, 34),
                (127, 35), (122, 38), (119, 31), (112, 22), (107, 16),
                (103, 8), (99, 10), (96, 15), (92, 21), (88, 22),
                (83, 18), (78, 9), (75, 17), (70, 22), (64, 25),
                (58, 26), (52, 28), (48, 30), (43, 28), (39, 22),
                (35, 29), (36, 36), (30, 36), (26, 38), (22, 37),
                (18, 40), (13, 44), (8, 44), (3, 43), (0, 39),
                (-3, 37), (-7, 36), (-10, 37)],
    "uk": [(-5, 50), (-3, 53), (-5, 56), (-2, 58), (0, 53), (1, 51)],
    "japan": [(130, 31), (132, 34), (137, 36), (140, 39), (142, 43),
              (141, 40), (137, 35), (133, 34), (131, 33)],
    "australia": [(114, -22), (114, -32), (119, -35), (125, -33),
                  (131, -32), (136, -35), (141, -38), (147, -39),
                  (150, -37), (153, -27), (150, -22), (146, -19),
                  (142, -11), (136, -12), (131, -12), (125, -14),
                  (121, -17), (117, -20)],
    "nz": [(167, -45), (171, -42), (175, -39), (177, -38), (174, -41),
           (169, -44)],
    "borneo": [(109, 1), (113, 4), (117, 6), (119, 1), (117, -3),
               (111, -3), (109, -2)],
    "new_guinea": [(131, -1), (136, -2), (141, -3), (146, -6), (147, -9),
                   (141, -8), (135, -4), (132, -3)],
    "madagascar": [(44, -16), (47, -15), (50, -16), (47, -24), (44, -25),
                   (43, -20)],
}


def draw_map(d, box):
    d.rectangle(box, fill=SEA)
    for pts in LANDMASSES.values():
        poly = [_lonlat(lon, lat, box) for lon, lat in pts]
        d.polygon(poly, fill=LAND)
    x0, y0, x1, y1 = box
    ey = _lonlat(0, 0, box)[1]
    d.line([(x0, ey), (x1, ey)], fill=LAND_LINE, width=1)


def draw_pins(d, box):
    """Numbered pins with generic de-collision: a pin whose circle would
    overlap an earlier one is pushed away; a leader line joins it to the
    true spot (small navy dot). Returns the list of displaced pin numbers."""
    placed = []  # (cx, cy)
    displaced = []
    for num in sorted(PINS):
        lon, lat = PINS[num]
        tx, ty = _lonlat(lon, lat, box)
        cx, cy = tx, ty
        for _ in range(24):
            clash = None
            for (px, py) in placed:
                if (cx - px) ** 2 + (cy - py) ** 2 < 14.0 ** 2:
                    clash = (px, py)
                    break
            if clash is None:
                break
            px, py = clash
            dx, dy = cx - px, cy - py
            if dx == 0 and dy == 0:
                dx, dy = 1, -1
            n = math.hypot(dx, dy)
            cx += dx / n * 3.0
            cy += dy / n * 3.0
        if (cx, cy) != (tx, ty):
            displaced.append(num)
            d.line([(tx, ty), (cx, cy)], fill=NAVY, width=1)
            d.ellipse([tx - 2, ty - 2, tx + 2, ty + 2], fill=NAVY)
        d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=NAVY,
                  outline=WHITE, width=1)
        f = sans_b(10)
        t = str(num)
        d.text((cx - f.getlength(t) / 2, cy - 5), t, font=f, fill=WHITE)
        note_dense(cy - 5, cy + 5)
        placed.append((cx, cy))
    return displaced


# ---- layout pieces ----

def draw_top_bar(d):
    d.rectangle([0, 0, W, TOP_H], fill=NAVY)
    f = sans_b(11)
    d.text((24, 3), "THE WORLD IN ONE DAY", font=f, fill=WHITE)
    r = "26 STORIES \u00b7 7 REGIONS \u00b7 ALL FROM THIS ONE DAY"
    d.text((W - 24 - f.getlength(r), 3), r, font=f, fill=WHITE)
    note_dense(3, 14)


def masthead_advance(size, track):
    f = playfair(size)
    return sum(f.getlength(ch) * track for ch in "Tuesday 24 November 2026")


def draw_masthead(d):
    """82px tracked Playfair date masthead. Returns (ink_top, ink_bottom)."""
    size, track, stroke = MAST_SIZE, MAST_TRACK, MAST_STROKE
    adv = masthead_advance(size, track)
    assert adv <= 1004, f"masthead advance {adv:.0f} overflows"
    x0 = (W - adv) / 2
    draw_tracked(d, "Tuesday 24 November 2026", size, track, stroke, x0,
                 MAST_Y, fill=INK)
    return x0, adv


def masthead_cap_band_runs(img):
    """Render-based gap check: count white-column-separated ink runs in the
    cap-height band (y=40..70) of the masthead. 21 glyphs (no spaces) should
    give 21 runs = zero letters touching in the letter bodies. (The
    getbbox-based version was wrong: PIL getbbox returns advance-box bounds,
    not ink, and reported phantom overlaps.)"""
    gray = img.convert("L")
    px = gray.load()
    cols = [any(px[x, y] < 128 for y in range(40, 70))
            for x in range(W)]
    runs = 0
    in_run = False
    for c in cols:
        if c and not in_run:
            runs += 1
            in_run = True
        elif not c and in_run:
            in_run = False
    return runs


def draw_region_bar(d):
    y0, y1 = REGION_Y, REGION_Y + REGION_H
    total = sum(n for _n, n in REGIONS)
    x = MX
    shades = [(24, 38, 58), (34, 52, 76), (44, 64, 92), (28, 48, 70),
              (38, 58, 82), (30, 44, 64), (48, 68, 96)]
    f = sans_b(11)
    for i, (name, n) in enumerate(REGIONS):
        wseg = CW * n / total
        d.rectangle([x, y0, x + wseg, y1], fill=shades[i % len(shades)])
        lab = f"{name} {n}"
        d.text((x + (wseg - f.getlength(lab)) / 2, y0 + 4), lab, font=f,
               fill=WHITE)
        x += wseg
    note_dense(y0 + 4, y0 + 15)


def draw_utc_strip(d):
    # v4 redesign (fixes the v3 defect: the rule + dot struck through the
    # hour digits). Stacked layout: hour ABOVE the rule, dot ON the rule,
    # label BELOW. Nothing may touch the hour digits.
    y0, y1 = UTC_Y, UTC_Y + UTC_H
    col = CW / len(UTC_POINTS)
    ft, fl = sans_b(13), sans(9)
    # rule first, then dots on top of it
    d.line([(MX, y0 + 20), (MX + CW, y0 + 20)], fill=GREY, width=1)
    for i, (tm, lab) in enumerate(UTC_POINTS):
        cx = MX + col * (i + 0.5)
        d.ellipse([cx - 4, y0 + 16, cx + 4, y0 + 24], fill=NAVY)
        d.text((cx - ft.getlength(tm) / 2, y0 + 2), tm, font=ft, fill=NAVY)
        d.text((cx - fl.getlength(lab) / 2, y0 + 25), lab, font=fl,
               fill=INK_SOFT)
    note_dense(y0 + 2, y0 + 34)


def draw_label(d, x, y, num, text, width):
    """Number badge + location line; 10px, shrinks to the 9px floor."""
    d.ellipse([x, y, x + 15, y + 15], fill=NAVY)
    nf = sans_b(10)
    nt = str(num)
    d.text((x + 7.5 - nf.getlength(nt) / 2, y + 2), nt, font=nf, fill=WHITE)
    size = 10
    f = sans_b(size)
    while size > 9 and f.getlength(text) > width - 22:
        size -= 1
        f = sans_b(size)
    d.text((x + 21, y + 3), text, font=f, fill=INK)
    note_dense(y + 3, y + 3 + size)
    return size


def draw_tag_chip(d, box, word):
    x0, y0, x1, _y1 = box
    f = sans_b(12)
    tw = f.getlength(word) + 10
    d.rectangle([x1 - tw, y0, x1, y0 + 16], fill=TAG_COL.get(word, NAVY))
    d.text((x1 - tw + 5, y0 + 3), word, font=f, fill=WHITE)
    note_dense(y0 + 3, y0 + 15)


def draw_lead(d, num, headline, deck, label, tag, scene, x, y):
    art = (x, y, x + LEAD_W, y + LEAD_ART_H)
    SCENES[scene](d, art)
    draw_tag_chip(d, art, tag)
    hy = y + LEAD_ART_H + 6
    lines = wrap(headline, sans_b(32), LEAD_W, max_lines=2)
    for ln in lines:
        d.text((x, hy), ln, font=sans_b(32), fill=INK)
        hy += 36
    dy = hy + 4
    assert sans(13).getlength(deck) <= LEAD_W, f"lead deck overflow: {deck}"
    d.text((x, dy), deck, font=sans(13), fill=INK_SOFT)
    note_dense(dy, dy + 13)
    ly = dy + 17 + 4
    draw_label(d, x, ly, num, label, LEAD_W - 22)
    return y + LEAD_H


def draw_numbers_box(d, x, y):
    wbox, hbox = NUM_W, LEAD_H
    d.rectangle([x, y, x + wbox, y + hbox], fill=NAVY_BOX)
    fh = sans_b(11)
    head = "THE DAY IN NUMBERS"
    d.text((x + (wbox - fh.getlength(head)) / 2, y + 2), head, font=fh,
           fill=(220, 190, 90))
    note_dense(y + 2, y + 13)
    colw = (wbox - 16) / 2
    row_y = y + 18
    for i, (val, lab, src) in enumerate(NUMBERS):
        cx = x + 8 + (i % 2) * colw
        cy = row_y + (i // 2) * 62
        fv = sans_b(24)
        assert fv.getlength(val) <= colw, f"number overflow: {val}"
        d.text((cx, cy), val, font=fv, fill=WHITE)
        lab_lines = wrap(lab, sans(10), colw, max_lines=2)
        ly = cy + 28
        for ln in lab_lines:
            d.text((cx, ly), ln, font=sans(10), fill=(210, 220, 230))
            ly += 12
        note_dense(cy + 29, ly)
        sy = ly + 1
        assert sans(9).getlength(src) <= colw, f"source overflow: {src}"
        d.text((cx, sy), src, font=sans(9), fill=(160, 175, 190))
        note_dense(sy, sy + 9)


def draw_card(d, num, headline, deck, label, tag, scene, x, y, row):
    art = (x, y, x + CARD_W, y + CARD_ART_H)
    SCENES[scene](d, art)
    draw_tag_chip(d, art, tag)
    hy = y + CARD_ART_H + 5
    lines = wrap(headline, sans_b(24), CARD_W, max_lines=2)
    for ln in lines:
        d.text((x, hy), ln, font=sans_b(24), fill=INK)
        hy += 29
    dy = hy + 3
    assert sans(13).getlength(deck) <= CARD_W, f"card deck overflow: {deck}"
    d.text((x, dy), deck, font=sans(13), fill=INK_SOFT)
    note_dense(dy, dy + 13)
    ly = dy + 17 + 3
    draw_label(d, x, ly, num, label, CARD_W - 22)
    return y + CARD_H


def draw_briefs_and_map(d):
    y = BRIEF_Y
    col_w = 360
    cols = [MX, MX + col_w + 8]
    map_x = MX + col_w * 2 + 16
    map_w = MX + CW - map_x
    pitch = BRIEF_H / 7  # v4: 13 briefs in 2 cols of 7+6
    for i, (num, tag, text) in enumerate(BRIEFS):
        col = i // 7
        row = i % 7
        bx = cols[col]
        by = y + row * pitch + 2
        ft = sans_b(9)
        d.text((bx, by + 3), tag, font=ft, fill=TAG_COL.get(tag, NAVY))
        tw = ft.getlength(tag) + 6
        f15 = sans(15)
        assert f15.getlength(text) <= col_w - tw, f"brief overflow: {text}"
        d.text((bx + tw, by), text, font=f15, fill=INK)
        note_dense(by, by + 15)
    map_box = (map_x, y, map_x + map_w, y + BRIEF_H)
    draw_map(d, map_box)
    displaced = draw_pins(d, map_box)
    d.rectangle(map_box, outline=GREY, width=1)
    return displaced


def draw_date_check(d):
    y0, y1 = DC_Y, DC_Y + DC_H
    d.rectangle([MX, y0, MX + CW, y1], fill=(232, 238, 244),
                outline=NAVY, width=1)
    # Title is a bold inline prefix on line 1. (A tab straddling the top
    # border would overlap the briefs' descenders in the row above the box,
    # so the tab design was dropped; the text must fit the box: 4 lines max.)
    prefix = "DATE CHECK \u2014 "
    f14, fb14 = sans(14), sans_b(14)
    pw = fb14.getlength(prefix)
    words = DATE_CHECK.split()
    lines = []
    cur = prefix
    cur_w = pw
    for w in words:
        sep = " " if cur != prefix else ""
        if cur_w + f14.getlength(sep + w) <= CW - 8:
            cur += sep + w
            cur_w += f14.getlength(sep + w)
        else:
            lines.append(cur)
            cur = w
            cur_w = f14.getlength(w)
    if cur:
        lines.append(cur)
    assert len(lines) <= 4, f"DATE CHECK wraps to {len(lines)} lines"
    ly = y0 + 8
    for i, ln in enumerate(lines):
        if i == 0:
            d.text((MX + 4, ly), prefix, font=fb14, fill=NAVY)
            d.text((MX + 4 + pw, ly), ln[len(prefix):], font=f14, fill=INK)
        else:
            d.text((MX + 4, ly), ln, font=f14, fill=INK)
        note_dense(ly, ly + 14)
        ly += 16
    return len(lines)


def draw_footer(d):
    y = FOOT_Y
    for i, line in enumerate(FOOTER):
        f = sans(13)
        assert f.getlength(line) <= CW, f"footer overflow: {line}"
        d.text((MX + (CW - f.getlength(line)) / 2, y + i * 14), line,
               font=f, fill=INK_SOFT)
        note_dense(y + i * 14, y + i * 14 + 13)


def main():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    draw_top_bar(d)
    x0, adv = draw_masthead(d)
    draw_region_bar(d)
    draw_utc_strip(d)
    # leads + numbers box
    for i, (num, hl, deck, lab, tag, scene) in enumerate(LEADS):
        x = MX + i * (LEAD_W + 10)
        draw_lead(d, num, hl, deck, lab, tag, scene, x, LEAD_Y)
    draw_numbers_box(d, MX + 3 * LEAD_W + 3 * 10, LEAD_Y)
    # cards: 2 rows of 5 / 5
    rows = [CARDS[0:5], CARDS[5:10]]
    for ri, row in enumerate(rows):
        y = CARD_ROWS_Y[ri]
        for ci, (num, hl, deck, lab, tag, scene) in enumerate(row):
            x = MX + ci * (CARD_W + CARD_GAP)
            draw_card(d, num, hl, deck, lab, tag, scene, x, y, ri)
    displaced = draw_briefs_and_map(d)
    dc_lines = draw_date_check(d)
    draw_footer(d)

    out = os.path.join(HERE, "entry.png")
    img.save(out, optimize=True)

    # ---- measurement report ----
    px = img.load()
    last_ink = -1
    for yy in range(H - 1, -1, -1):
        for xx in range(W):
            if px[xx, yy] != PAPER:
                last_ink = yy
                break
        if last_ink >= 0:
            break
    first_ink = -1
    for yy in range(H):
        for xx in range(W):
            if px[xx, yy] != PAPER:
                first_ink = yy
                break
        if first_ink >= 0:
            break
    left_ink = min(xx for yy in range(H) for xx in range(W)
                   if px[xx, yy] != PAPER)
    right_ink = max(xx for yy in range(H) for xx in range(W)
                    if px[xx, yy] != PAPER)
    # ed-23 top-band metric: rows in y=10..200 with >30% dark pixels
    import collections
    gray = img.convert("L")
    gp = gray.load()
    dense_top = 0
    for yy in range(10, 200):
        dark = sum(1 for xx in range(W) if gp[xx, yy] < 100)
        if dark > 0.30 * W:
            dense_top += 1
    n_dense, bands = dense_row_count()
    ill = (3 * LEAD_W * LEAD_ART_H + 10 * CARD_W * CARD_ART_H) / (W * H) * 100
    print(f"masthead advance={adv:.0f} cap_band_runs={masthead_cap_band_runs(img)} (21 glyphs = zero touching in letter bodies)")
    print(f"date_check_lines={dc_lines} displaced_pins={displaced}")
    print(f"dense_rows(<16px)={n_dense} (budget <=80)")
    print(f"dense_top_band(y10-200)={dense_top} (ed-23 v7=108, bagarte=89)")
    print(f"illustration={ill:.2f}% (floor 17.2%)")
    print(f"ink: top={first_ink} bottom={last_ink} left={left_ink} right={right_ink}")
    print(f"bottom_margin={H - 1 - last_ink}px left_margin={left_ink}px "
          f"right_margin={W - 1 - right_ink}px")
    print(f"stories={len(LEADS) + len(CARDS) + len(BRIEFS)} "
          f"regions_total={sum(n for _n, n in REGIONS)}")
    assert last_ink <= 1016, f"bottom overflow: last ink y={last_ink}"
    assert n_dense <= 80, f"dense rows {n_dense} over budget 80"
    print("saved", out)


if __name__ == "__main__":
    main()
