#!/usr/bin/env python3
"""World news front page for Saturday 21 November 2026.

Draws a newspaper front page (1024x1024 PNG) with pure standard library:
its own bitmap font, its own raster drawing and its own PNG encoder.
No network, no clock, no randomness: every run writes identical bytes.
"""

import os
import struct
import zlib

# ---------------------------------------------------------------- font ----
# Each glyph is 7 rows of 5 pixels, "#" = ink, "." = empty.
FONT = {
    "A": ("..#..", ".#.#.", "#...#", "#...#", "#####", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", "..#..", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".....", ".##..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "%": ("##..#", "##.#.", "...#.", "..#..", ".#...", "#..##", "#.##."),
    "$": ("..#..", ".####", "#.#.#", ".###.", "..#.#", "####.", "..#.."),
    "/": ("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
    "&": (".##..", "#..#.", "#..#.", ".#...", "#.#.#", "#..#.", ".##.#"),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "=": (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    "*": (".....", ".#.#.", ".###.", "#####", ".###.", ".#.#.", "....."),
}

GLYPH_W = 5
GLYPH_H = 7
ADVANCE = 6  # glyph width + 1px gap, before scaling


def text_width(text, scale):
    return len(text) * ADVANCE * scale


def wrap_text(text, max_width, scale):
    """Greedy word wrap; returns a list of lines that fit max_width."""
    lines = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for word in words:
            trial = word if not cur else cur + " " + word
            if text_width(trial, scale) <= max_width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
    return lines


# -------------------------------------------------------------- canvas ----
class Canvas:
    def __init__(self, width, height, bg):
        self.w = width
        self.h = height
        self.buf = bytearray(width * height * 3)
        self.fill(0, 0, width, height, bg)

    def px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i] = color[0]
            self.buf[i + 1] = color[1]
            self.buf[i + 2] = color[2]

    def fill(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.buf[i] = color[0]
                self.buf[i + 1] = color[1]
                self.buf[i + 2] = color[2]

    def hline(self, x, y, w, color, thick=1):
        self.fill(x, y, w, thick, color)

    def vline(self, x, y, h, color, thick=1):
        self.fill(x, y, thick, h, color)

    def line(self, x0, y0, x1, y1, color, thick=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.fill(x0 - thick // 2, y0 - thick // 2, thick, thick, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.fill(cx - dx, cy + dy, 2 * dx + 1, 1, color)

    def circle(self, cx, cy, r, color, thick=1):
        steps = max(24, r * 6)
        for k in range(steps):
            import math
            a = 2 * math.pi * k / steps
            x = int(cx + r * math.cos(a) + 0.5)
            y = int(cy + r * math.sin(a) + 0.5)
            self.fill(x - thick // 2, y - thick // 2, thick, thick, color)

    def arc(self, cx, cy, r, a0, a1, color, thick=2):
        import math
        steps = max(8, int(r * abs(a1 - a0)))
        for k in range(steps + 1):
            a = a0 + (a1 - a0) * k / steps
            x = int(cx + r * math.cos(a) + 0.5)
            y = int(cy + r * math.sin(a) + 0.5)
            self.fill(x - thick // 2, y - thick // 2, thick, thick, color)

    def polygon(self, points, color):
        """Scanline fill for a simple polygon."""
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(points)
            for i in range(n):
                x0, y0 = points[i]
                x1, y1 = points[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                self.fill(int(xs[j]), y, int(xs[j + 1]) - int(xs[j]) + 1, 1, color)

    def glyph(self, x, y, scale, color, ch):
        rows = FONT.get(ch)
        if rows is None:
            rows = FONT["?"]
        for r, row in enumerate(rows):
            for c, bit in enumerate(row):
                if bit == "#":
                    self.fill(x + c * scale, y + r * scale, scale, scale, color)

    def text(self, x, y, scale, color, s, align="left"):
        w = text_width(s, scale)
        if align == "center":
            x -= w // 2
        elif align == "right":
            x -= w
        for ch in s:
            self.glyph(x, y, scale, color, ch)
            x += ADVANCE * scale
        return w

    def fit_scale(self, s, max_width, start, minimum=2):
        scale = start
        while scale > minimum and text_width(s, scale) > max_width:
            scale -= 1
        return scale


# ------------------------------------------------------------------ png ----
def write_png(path, canvas):
    w, h = canvas.w, canvas.h
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)  # filter: none
        raw += canvas.buf[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# ------------------------------------------------------------ pictograms ----
# Each pictogram draws inside a square box (x, y, size) with simple shapes.

def pic_globe(cv, x, y, s, ink, blue, red):
    cx, cy, r = x + s // 2, y + s // 2, s // 2 - 6
    cv.circle(cx, cy, r, blue, 4)
    cv.circle(cx, cy, r - 14, blue, 2)
    cv.line(cx - r, cy, cx + r, cy, blue, 2)
    cv.line(cx, cy - r, cx, cy + r, blue, 2)
    # factory silhouette with smoke, sitting on the globe's base
    base = cy + r - 8
    cv.fill(cx - 34, base - 34, 22, 34, ink)
    cv.fill(cx - 8, base - 24, 22, 24, ink)
    cv.fill(cx - 34, base - 52, 8, 20, ink)
    cv.disc(cx - 30, base - 60, 5, red)
    cv.disc(cx - 22, base - 70, 4, red)
    cv.disc(cx - 14, base - 78, 3, red)


def pic_bridge(cv, x, y, s, ink, blue, red):
    # suspension bridge: deck, two towers, cables, river below
    deck = y + s - 34
    cv.hline(x + 6, deck, s - 12, ink, 4)
    for tx in (x + s // 3, x + 2 * s // 3):
        cv.vline(tx, y + 18, deck - (y + 18), ink, 4)
    cv.line(x + s // 3, y + 18, x + 6, deck, ink, 2)
    cv.line(x + s // 3, y + 18, x + s // 2, deck, ink, 2)
    cv.line(x + 2 * s // 3, y + 18, x + s // 2, deck, ink, 2)
    cv.line(x + 2 * s // 3, y + 18, x + s - 6, deck, ink, 2)
    cv.line(x + s // 3, y + 18, x + 2 * s // 3, y + 18, ink, 2)
    cv.fill(x + 6, y + s - 22, s - 12, 5, blue)
    cv.fill(x + 6, y + s - 12, s - 12, 3, blue)
    # warning star above the deck
    cx, cy = x + s // 2, y + 8
    for dx, dy in ((0, -8), (6, -6), (8, 0), (6, 6), (0, 8),
                   (-6, 6), (-8, 0), (-6, -6)):
        cv.line(cx, cy, cx + dx, cy + dy, red, 3)
    cv.disc(cx, cy, 3, red)


def pic_chart_down(cv, x, y, s, ink, blue, red):
    # axes and a falling line with arrowhead
    cv.vline(x + 12, y + 10, s - 24, ink, 3)
    cv.hline(x + 12, y + s - 12, s - 24, ink, 3)
    pts = [(x + 16, y + 18), (x + s // 3, y + 30), (x + s // 2, y + 26),
           (x + 2 * s // 3, y + 52), (x + s - 16, y + s - 22)]
    for a, b in zip(pts, pts[1:]):
        cv.line(a[0], a[1], b[0], b[1], red, 4)
    cv.line(pts[-1][0], pts[-1][1], pts[-1][0] - 12, pts[-1][1] - 2, red, 4)
    cv.line(pts[-1][0], pts[-1][1], pts[-1][0] - 2, pts[-1][1] - 12, red, 4)
    # a chip in the corner
    cv.fill(x + s - 34, y + 12, 22, 22, blue)
    cv.fill(x + s - 29, y + 17, 12, 12, (246, 241, 229))


def pic_controller(cv, x, y, s, ink, blue, red):
    # game controller: body, d-pad, buttons, sticks
    cx, cy = x + s // 2, y + s // 2 + 4
    cv.polygon([(cx - 42, cy - 18), (cx + 42, cy - 18), (cx + 46, cy + 6),
                (cx + 30, cy + 26), (cx + 14, cy + 14), (cx - 14, cy + 14),
                (cx - 30, cy + 26), (cx - 46, cy + 6)], ink)
    cv.fill(cx - 34, cy - 8, 7, 20, (246, 241, 229))
    cv.fill(cx - 40, cy - 2, 19, 7, (246, 241, 229))
    for dx, dy, c in ((22, -8, red), (30, 0, blue), (22, 8, red),
                      (14, 0, blue)):
        cv.disc(cx + dx, cy + dy, 4, c)
    cv.disc(cx - 12, cy + 12, 5, (246, 241, 229))
    cv.disc(cx + 12, cy + 12, 5, (246, 241, 229))


def pic_cyclone(cv, x, y, s, ink, blue, red):
    import math
    cx, cy = x + s // 2, y + s // 2 - 4
    for r in range(8, s // 2 - 2, 8):
        cv.arc(cx, cy, r, 0.6, 4.6, blue, 3)
    cv.disc(cx, cy, 6, red)
    # rain drops below
    for dx in (-24, -8, 8, 24):
        cv.line(cx + dx, cy + s // 2 - 14, cx + dx - 4, cy + s // 2 - 2,
                blue, 3)
        cv.disc(cx + dx - 4, cy + s // 2, 3, blue)


def pic_servers(cv, x, y, s, ink, blue, red):
    # server rack with a tax tag
    cv.fill(x + 14, y + 8, s - 28, s - 16, ink)
    for i in range(4):
        yy = y + 16 + i * (s - 32) // 4
        cv.fill(x + 20, yy, s - 40, (s - 32) // 4 - 8, (246, 241, 229))
        cv.disc(x + 28, yy + ((s - 32) // 4 - 8) // 2, 3, blue)
        cv.disc(x + 38, yy + ((s - 32) // 4 - 8) // 2, 3, red)
    # dollar tag
    cv.disc(x + s - 22, y + s - 22, 14, red)
    cv.text(x + s - 22, y + s - 32, 2, (246, 241, 229), "$", align="center")



# -------------------------------------------------------------- layout ----
PAPER = (246, 241, 229)
INK = (26, 26, 26)
RED = (176, 32, 32)
BLUE = (31, 78, 121)
GREY = (110, 105, 92)

W, H = 1024, 1024


def draw_masthead(cv):
    cv.hline(24, 8, W - 48, INK, 4)
    cv.text(W // 2, 18, 7, INK, "THE WORLD TODAY", align="center")
    cv.hline(24, 78, W - 48, INK, 3)
    cv.text(W // 2, 88, 3, RED, "SATURDAY 21 NOVEMBER 2026", align="center")
    cv.text(24, 90, 2, GREY, "NO. 325", align="left")
    cv.text(W - 24, 90, 2, GREY, "ONE DAY - ONE PAGE", align="right")
    cv.hline(24, 122, W - 48, INK, 2)


def draw_lead(cv, y):
    cv.text(24, y + 6, 3, RED, "CLIMATE SUMMIT - ANTALYA, TURKEY")
    cv.text(24, y + 36, 6, INK, "CLIMATE TALKS RUN")
    cv.text(24, y + 84, 6, INK, "INTO OVERTIME")
    summary = ("NEARLY 200 NATIONS ARE STILL DEADLOCKED IN ANTALYA ON "
               "SATURDAY. THE DRAFT DEAL DROPS EVERY MENTION OF "
               "FOSSIL FUELS.")
    lines = wrap_text(summary, 640, 3)
    yy = y + 134
    for ln in lines:
        cv.text(24, yy, 3, INK, ln)
        yy += 26
    pic_globe(cv, 716, y + 24, 210, INK, BLUE, RED)
    return y + 240


def draw_band(cv, y, kicker, headline, summary, pic):
    pic(cv, 28, y + 6, 96, INK, BLUE, RED)
    tx = 140
    cv.text(tx, y + 8, 2, RED, kicker)
    cv.text(tx, y + 28, 4, INK, headline)
    lines = wrap_text(summary, W - 24 - tx, 3)
    yy = y + 66
    for ln in lines[:2]:
        cv.text(tx, yy, 3, INK, ln)
        yy += 26
    return y + 116


def draw_page():
    cv = Canvas(W, H, PAPER)
    cv.hline(0, 0, W, INK, 6)
    cv.hline(0, H - 6, W, INK, 6)
    cv.vline(0, 0, H, INK, 6)
    cv.vline(W - 6, 0, H, INK, 6)

    draw_masthead(cv)
    y = draw_lead(cv, 132)
    cv.hline(24, y + 4, W - 48, INK, 2)

    y += 12
    y = draw_band(
        cv, y, "WAR IN EUROPE - WARSAW, POLAND",
        "NATO CHIEF IN WARSAW",
        "RUTTE IN WARSAW TODAY AFTER TWO RUSSIAN MISSILES CAME DOWN. "
        "KYIV COUNTS NINE DEAD.",
        pic_bridge)
    cv.hline(24, y - 6, W - 48, GREY, 1)

    y = draw_band(
        cv, y, "MARKETS - NEW YORK",
        "ANTHROPIC DOWN 9% ON DAY TWO",
        "SHARES SLID TO $88.30 ON DAY TWO OF THE RECORD IPO AS THE "
        "S AND P 500 FELL INTO CORRECTION.",
        pic_chart_down)
    cv.hline(24, y - 6, W - 48, GREY, 1)

    y = draw_band(
        cv, y, "ENTERTAINMENT - LOS ANGELES",
        "GTA VI: $3.79 BILLION IN A DAY",
        "THE BIGGEST ENTERTAINMENT LAUNCH EVER. 32.5 MILLION COPIES "
        "SOLD BEFORE RELEASE.",
        pic_controller)
    cv.hline(24, y - 6, W - 48, GREY, 1)

    y = draw_band(
        cv, y, "WEATHER - INDIA",
        "CYCLONE AKVAN WEAKENS",
        "THE STORM CROSSED ODISHA'S COAST WITH HEAVY RAIN, AND IS "
        "NOW FADING INTO A DEEP DEPRESSION.",
        pic_cyclone)
    cv.hline(24, y - 6, W - 48, GREY, 1)

    y = draw_band(
        cv, y, "TECH POLICY - WASHINGTON",
        "TRUMP: TAX ON DATA CENTRES ABROAD",
        "US FIRMS BUILDING AI DATA CENTRES OVERSEAS FACE A TREMENDOUS "
        "TAX, THE PRESIDENT SAID ON FRIDAY.",
        pic_servers)
    cv.hline(24, y - 6, W - 48, INK, 2)

    cv.text(W // 2, y + 6, 3, INK,
            "SPORT - INDIA 159/1 AT STUMPS, DAY TWO, WELLINGTON",
            align="center")
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = draw_page()
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path, cv)
    print(f"wrote {path} ({size} bytes)")


if __name__ == "__main__":
    main()
