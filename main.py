#!/usr/bin/env python3
"""The picture that tastes of one ingredient.

Draws one delicious picture with code: a steaming bowl of ramen —
glistening golden broth, glossy noodles lifted by chopsticks, a soft
egg, chashu and spring onions — big in frame on a warm, clean
background so it still reads delicious at ~300px.

Pure Python 3.13 stdlib only. Writes /output/entry.png (or
$OUTPUT_DIR/entry.png for local testing).
"""

import math
import os
import struct
import zlib

W, H = 900, 900
buf = bytearray(W * H * 3)


def setpx(x, y, r, g, b):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = r
        buf[i + 1] = g
        buf[i + 2] = b


def blend(x, y, r, g, b, a):
    if a <= 0:
        return
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        if a >= 1:
            buf[i] = r
            buf[i + 1] = g
            buf[i + 2] = b
        else:
            buf[i] = int(buf[i] + (r - buf[i]) * a)
            buf[i + 1] = int(buf[i + 1] + (g - buf[i + 1]) * a)
            buf[i + 2] = int(buf[i + 2] + (b - buf[i + 2]) * a)


def ellipse(cx, cy, rx, ry, color, a=1.0):
    r, g, b = color
    y0 = max(0, cy - ry)
    y1 = min(H - 1, cy + ry)
    for yy in range(y0, y1 + 1):
        dy = (yy - cy) / ry
        rest = 1.0 - dy * dy
        if rest <= 0:
            continue
        dx = rx * math.sqrt(rest)
        x0 = max(0, int(cx - dx))
        x1 = min(W - 1, int(cx + dx))
        base = yy * W
        if a >= 1:
            for xx in range(x0, x1 + 1):
                i = (base + xx) * 3
                buf[i] = r
                buf[i + 1] = g
                buf[i + 2] = b
        else:
            for xx in range(x0, x1 + 1):
                i = (base + xx) * 3
                buf[i] = int(buf[i] + (r - buf[i]) * a)
                buf[i + 1] = int(buf[i + 1] + (g - buf[i + 1]) * a)
                buf[i + 2] = int(buf[i + 2] + (b - buf[i + 2]) * a)


def disc(cx, cy, rad, color, a=1.0):
    ellipse(cx, cy, rad, rad, color, a)


def hline(x0, x1, y, color, a=1.0):
    r, g, b = color
    if not (0 <= y < H):
        return
    x0 = max(0, x0)
    x1 = min(W - 1, x1)
    base = y * W
    if a >= 1:
        for xx in range(x0, x1 + 1):
            i = (base + xx) * 3
            buf[i] = r
            buf[i + 1] = g
            buf[i + 2] = b
    else:
        for xx in range(x0, x1 + 1):
            i = (base + xx) * 3
            buf[i] = int(buf[i] + (r - buf[i]) * a)
            buf[i + 1] = int(buf[i + 1] + (g - buf[i + 1]) * a)
            buf[i + 2] = int(buf[i + 2] + (b - buf[i + 2]) * a)


def line(x0, y0, x1, y1, w, color, a=1.0):
    steps = int(max(abs(x1 - x0), abs(y1 - y0)) / max(2, w * 0.5)) + 1
    for i in range(steps + 1):
        t = i / steps
        disc(int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t), max(1, w // 2), color, a)


def in_broth(x, y):
    return ((x - 450) / 300.0) ** 2 + ((y - 545) / 128.0) ** 2 <= 1.0


def strand(x0, x1, ybase, amp, waves, phase, w, color, a=1.0):
    n = max(2, (x1 - x0) // 3)
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i // n
        y = int(ybase + amp * math.sin(phase + (x - x0) / float(x1 - x0) * waves * 2 * math.pi))
        if in_broth(x, y):
            disc(x, y, max(1, w // 2), color, a)


def row_gradient(y0, y1, top, bot):
    for y in range(y0, min(H, y1)):
        t = (y - y0) / max(1, (y1 - y0 - 1))
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        buf[y * W * 3:(y + 1) * W * 3] = bytes((r, g, b)) * W


def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += buf[y * W * 3:(y + 1) * W * 3]
    comp = zlib.compress(bytes(raw), 6)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def draw():
    # -- warm background + glow -------------------------------------------
    row_gradient(0, H, (247, 232, 200), (226, 190, 132))
    ellipse(450, 480, 430, 330, (255, 214, 140), 0.25)
    # -- wooden table ------------------------------------------------------
    row_gradient(640, H, (176, 128, 84), (148, 102, 64))
    for yy in (700, 770, 840):
        hline(0, W - 1, yy, (120, 80, 48), 0.18)
    # -- soft shadow under the bowl ---------------------------------------
    ellipse(450, 738, 330, 42, (60, 35, 18), 0.28)
    # -- bowl: dark lacquer body, opening, golden broth -------------------
    ellipse(450, 600, 335, 165, (44, 26, 18))
    ellipse(450, 585, 335, 150, (58, 32, 22))
    ellipse(450, 545, 320, 140, (24, 14, 10))
    ellipse(450, 545, 300, 128, (217, 138, 43))
    # broth light: warm pool in the middle
    ellipse(430, 520, 260, 105, (238, 164, 66), 0.55)
    ellipse(425, 512, 200, 80, (245, 183, 88), 0.45)
    ellipse(420, 505, 130, 55, (250, 200, 110), 0.4)
    # broth depth at the bottom edge
    ellipse(450, 612, 280, 55, (180, 105, 30), 0.35)
    # oil glints on the broth
    for (gx, gy, gr) in ((360, 480, 26), (520, 455, 20), (620, 520, 24), (300, 560, 16)):
        ellipse(gx, gy, gr, gr // 2, (255, 220, 130), 0.5)
    # -- noodles: wavy strands across the broth ---------------------------
    for i in range(12):
        yb = 480 + i * 11
        dy = (yb - 545) / 128.0
        rest = 1.0 - dy * dy
        if rest <= 0:
            continue
        dx = int(300 * math.sqrt(rest)) - 8
        x0, x1 = 450 - dx, 450 + dx
        strand(x0, x1, yb, 14, 2.2 + (i % 3) * 0.5, i * 1.3, 6, (209, 160, 55))
        strand(x0, x1, yb - 3, 14, 2.2 + (i % 3) * 0.5, i * 1.3, 6, (247, 215, 119))
    # -- noodles lifted by the chopsticks ----------------------------------
    for k in range(7):
        x0, y0 = 596 + k * 13, 482 - k * 6
        x1, y1 = 664 + k * 10, 330
        steps = 26
        for s in range(steps + 1):
            t = s / steps
            x = int(x0 + (x1 - x0) * t + 12 * math.sin(t * 9 + k))
            y = int(y0 + (y1 - y0) * t)
            disc(x, y, 4, (247, 215, 119))
    # -- chopsticks ---------------------------------------------------------
    line(770, 150, 655, 320, 13, (107, 66, 38))
    line(795, 180, 680, 335, 13, (96, 58, 32))
    line(766, 158, 658, 314, 4, (150, 100, 60), 0.8)
    line(791, 188, 683, 329, 4, (140, 92, 54), 0.8)
    # -- soft egg -----------------------------------------------------------
    disc(320, 500, 54, (253, 246, 233))
    disc(330, 510, 44, (240, 224, 196), 0.5)
    disc(320, 500, 27, (245, 158, 27))
    disc(310, 490, 9, (255, 196, 90), 0.8)
    # -- chashu slices ------------------------------------------------------
    ellipse(560, 580, 62, 48, (216, 136, 115))
    ellipse(560, 580, 38, 28, (190, 100, 80))
    ellipse(560, 580, 16, 12, (226, 160, 140))
    ellipse(640, 540, 55, 42, (216, 136, 115))
    ellipse(640, 540, 33, 24, (190, 100, 80))
    ellipse(640, 540, 14, 10, (226, 160, 140))
    # -- spring onions, sesame, chili --------------------------------------
    onions = [(400, 470), (470, 440), (540, 470), (380, 600), (480, 610),
              (590, 640), (680, 590), (350, 530), (520, 600), (440, 650),
              (610, 450), (300, 600)]
    for (ox, oy) in onions:
        if in_broth(ox, oy):
            disc(ox, oy, 7, (46, 130, 62))
            disc(ox, oy, 3, (120, 190, 90))
    import random
    rnd = random.Random(7)
    for _ in range(26):
        sx = rnd.randint(200, 700)
        sy = rnd.randint(440, 650)
        if in_broth(sx, sy):
            disc(sx, sy, 2, (255, 244, 214) if rnd.random() < 0.6 else (60, 40, 20), 0.85)
    for (cx0, cy0, cx1, cy1) in ((500, 470, 540, 462), (480, 640, 520, 648), (380, 620, 410, 612)):
        line(cx0, cy0, cx1, cy1, 2, (200, 60, 50))
    # -- steam rising off the broth ----------------------------------------
    for sx in (340, 420, 500, 570):
        for k in range(12):
            y = 395 - k * 24
            x = int(sx + 16 * math.sin(k * 0.8 + sx))
            ellipse(x, y, 30 + k, 16, (255, 255, 255), 0.15)
    # -- bright rim highlight, top-left ------------------------------------
    for k in range(26):
        t = k / 25.0
        ang = math.pi + t * math.pi * 0.55
        x = int(450 + 314 * math.cos(ang))
        y = int(545 + 134 * math.sin(ang))
        disc(x, y, 3, (255, 235, 190), 0.5)
    # -- big soft gloss on the broth ---------------------------------------
    ellipse(400, 490, 150, 55, (255, 215, 130), 0.35)
    ellipse(590, 480, 90, 38, (255, 225, 150), 0.3)


def main():
    out = os.environ.get("OUTPUT_DIR", "/output")
    os.makedirs(out, exist_ok=True)
    draw()
    write_png(os.path.join(out, "entry.png"))


if __name__ == "__main__":
    main()
