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


# ---------------------------------------------------------------- pixel buffer
class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)

    def blend(self, x, y, r, g, b, a=1.0):
        if x < 0 or y < 0 or x >= self.w or y >= self.h or a <= 0:
            return
        i = (y * self.w + x) * 3
        if a >= 1.0:
            self.px[i] = r
            self.px[i + 1] = g
            self.px[i + 2] = b
        else:
            self.px[i] = int(r * a + self.px[i] * (1 - a))
            self.px[i + 1] = int(g * a + self.px[i + 1] * (1 - a))
            self.px[i + 2] = int(b * a + self.px[i + 2] * (1 - a))

    def circle(self, cx, cy, rad, color, alpha=1.0):
        r, g, b = color
        x0 = max(0, int(cx - rad))
        x1 = min(self.w - 1, int(cx + rad) + 1)
        y0 = max(0, int(cy - rad))
        y1 = min(self.h - 1, int(cy + rad) + 1)
        rr = rad * rad
        for y in range(y0, y1 + 1):
            dy = y - cy
            dx = math.sqrt(max(0.0, rr - dy * dy))
            for x in range(max(x0, int(cx - dx)), min(x1, int(cx + dx)) + 1):
                self.blend(x, y, r, g, b, alpha)

    def ellipse(self, cx, cy, rx, ry, color, alpha=1.0):
        r, g, b = color
        x0 = max(0, int(cx - rx))
        x1 = min(self.w - 1, int(cx + rx) + 1)
        y0 = max(0, int(cy - ry))
        y1 = min(self.h - 1, int(cy + ry) + 1)
        for y in range(y0, y1 + 1):
            t = (y - cy) / ry
            dx = rx * math.sqrt(max(0.0, 1 - t * t))
            for x in range(max(x0, int(cx - dx)), min(x1, int(cx + dx)) + 1):
                self.blend(x, y, r, g, b, alpha)

    def ring(self, cx, cy, rx, ry, thick, color, alpha=1.0):
        # Elliptical ring: draw outer, then punch inner with background is
        # hard, so draw as many small segments instead — approximate by
        # drawing outer ellipse then inner ellipse in the caller's bg color.
        self.ellipse(cx, cy, rx, ry, color, alpha)

    def hline(self, x0, x1, y, color, alpha=1.0):
        r, g, b = color
        for x in range(max(0, x0), min(self.w - 1, x1) + 1):
            self.blend(x, y, r, g, b, alpha)

    def line(self, x0, y0, x1, y1, width, color, alpha=1.0):
        n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 2
        for i in range(n + 1):
            t = i / n
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t
            self.circle(x, y, width / 2.0, color, alpha)

    def bezier(self, pts, width, color, alpha=1.0, steps=60):
        # pts: list of (x, y) control points (cubic if 4, quadratic if 3)
        prev = None
        for i in range(steps + 1):
            t = i / steps
            if len(pts) == 4:
                mt = 1 - t
                x = (mt ** 3 * pts[0][0] + 3 * mt * mt * t * pts[1][0]
                     + 3 * mt * t * t * pts[2][0] + t ** 3 * pts[3][0])
                y = (mt ** 3 * pts[0][1] + 3 * mt * mt * t * pts[1][1]
                     + 3 * mt * t * t * pts[2][1] + t ** 3 * pts[3][1])
            else:
                mt = 1 - t
                x = mt * mt * pts[0][0] + 2 * mt * t * pts[1][0] + t * t * pts[2][0]
                y = mt * mt * pts[0][1] + 2 * mt * t * pts[1][1] + t * t * pts[2][1]
            if prev is not None:
                self.line(prev[0], prev[1], x, y, width, color, alpha)
            prev = (x, y)

    def poly(self, points, color, alpha=1.0):
        # Scanline fill of a simple polygon.
        r, g, b = color
        ys = [p[1] for p in points]
        y0, y1 = int(min(ys)), int(max(ys))
        n = len(points)
        for y in range(max(0, y0), min(self.h - 1, y1) + 1):
            xs = []
            for i in range(n):
                x0, yy0 = points[i]
                x1, yy1 = points[(i + 1) % n]
                if (yy0 <= y < yy1) or (yy1 <= y < yy0):
                    t = (y - yy0) / (yy1 - yy0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                for x in range(max(0, int(xs[j])), min(self.w - 1, int(xs[j + 1])) + 1):
                    self.blend(x, y, r, g, b, alpha)


# ---------------------------------------------------------------- PNG encoder
def write_png(path, canvas):
    def chunk(ctype, data):
        c = struct.pack(">I", len(data)) + ctype + data
        c += struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
        return c

    w, h = canvas.w, canvas.h
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter: none
        raw += canvas.px[y * w * 3:(y + 1) * w * 3]
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ---------------------------------------------------------------- the picture
def draw():
    c = Canvas(W, H)

    # Warm cream background, soft vertical gradient + warm glow at centre.
    for y in range(H):
        t = y / H
        r = int(250 - 18 * t)
        g = int(232 - 34 * t)
        b = int(205 - 42 * t)
        row = bytes((r, g, b)) * W
        c.px[y * W * 3:(y + 1) * W * 3] = row
    # Warm radial glow behind the bowl.
    for y in range(120, 760):
        for x in range(60, 840):
            dx = (x - 450) / 430.0
            dy = (y - 470) / 360.0
            d = dx * dx + dy * dy
            if d < 1.0:
                a = (1 - d) * 0.16
                c.blend(x, y, 255, 214, 150, a)

    # Wooden table band along the bottom.
    for y in range(700, H):
        t = (y - 700) / 200.0
        r = int(176 - 30 * t)
        g = int(128 - 26 * t)
        b = int(82 - 18 * t)
        c.px[y * W * 3:(y + 1) * W * 3] = bytes((r, g, b)) * W
    c.hline(0, W - 1, 700, (120, 82, 48), 0.55)
    c.hline(0, W - 1, 790, (120, 82, 48), 0.35)

    # Soft shadow under the bowl.
    c.ellipse(450, 742, 330, 42, (90, 55, 25), 0.28)

    # Bowl body: deep indigo ceramic, wide and generous.
    c.ellipse(450, 585, 335, 195, (38, 46, 68))
    c.ellipse(450, 578, 335, 195, (30, 37, 56))
    # Bowl foot ring.
    c.ellipse(450, 758, 150, 26, (22, 28, 44))
    # Bowl rim highlight (top edge catching light).
    c.ellipse(450, 512, 335, 118, (52, 64, 92))
    # Rim band.
    c.ellipse(450, 520, 318, 108, (64, 76, 106))
    # Broth: rich golden, glowing.
    c.ellipse(450, 522, 296, 96, (216, 138, 43))
    c.ellipse(450, 520, 282, 88, (232, 164, 62))
    c.ellipse(450, 516, 250, 74, (240, 178, 80))
    # Broth gloss: soft sheen upper-left, kept small so it reads as
    # light on liquid, not a flat patch.
    c.ellipse(355, 488, 90, 20, (255, 214, 130), 0.35)
    c.ellipse(330, 482, 44, 11, (255, 232, 170), 0.5)

    # ---- noodles swirling in the broth
    noodle_dark = (206, 138, 32)
    noodle = (244, 196, 88)
    noodle_hi = (255, 222, 140)
    swirls = [
        [(300, 540), (360, 500), (430, 540), (470, 505)],
        [(330, 560), (400, 520), (470, 560), (520, 520)],
        [(380, 575), (450, 540), (520, 575), (570, 540)],
        [(280, 520), (350, 545), (420, 515), (480, 545)],
        [(420, 560), (500, 525), (560, 555), (610, 525)],
        [(340, 495), (410, 520), (480, 492), (540, 518)],
        [(470, 585), (540, 550), (600, 580), (640, 548)],
        [(250, 545), (320, 570), (390, 545), (440, 570)],
    ]
    for s in swirls:
        c.bezier(s, 9, noodle_dark, 0.9)
        c.bezier([(x, y - 3) for x, y in s], 5, noodle, 0.95)
        c.bezier([(x, y - 5) for x, y in s], 2, noodle_hi, 0.9)

    # ---- chashu: two glistening slices, rose-pink with a darker swirl
    # Soft contact shadows so the slices sit IN the broth, not on it.
    c.ellipse(588, 512, 62, 34, (150, 90, 30), 0.25)
    c.ellipse(643, 556, 50, 28, (150, 90, 30), 0.25)
    for (cx, cy, rad) in [(585, 500, 62), (640, 545, 50)]:
        c.circle(cx, cy, rad, (232, 165, 150))
        c.circle(cx, cy, rad - 12, (226, 140, 126))
        c.circle(cx, cy, rad - 26, (240, 180, 162))
        c.circle(cx, cy, rad - 38, (214, 122, 110))
        c.circle(cx - 14, cy - 16, 12, (255, 205, 190), 0.8)

    # ---- soft egg: white with a jammy orange yolk
    c.circle(315, 505, 56, (252, 246, 232))
    c.circle(315, 505, 56, (240, 228, 205), 0.0)
    c.circle(315, 505, 30, (240, 140, 30))
    c.circle(315, 505, 22, (248, 158, 44))
    c.circle(305, 495, 9, (255, 196, 90), 0.9)

    # ---- nori sheet standing at the back of the bowl
    c.poly([(600, 470), (660, 430), (672, 500), (612, 540)], (32, 66, 38))
    c.poly([(608, 468), (656, 436), (664, 496), (616, 532)], (44, 86, 50))

    # ---- spring onion rings scattered on the broth
    for (cx, cy, rad) in [(270, 500, 12), (420, 480, 11), (500, 545, 12),
                          (560, 575, 10), (380, 580, 11), (470, 505, 10),
                          (610, 580, 11), (300, 565, 10)]:
        c.circle(cx, cy, rad, (74, 148, 66))
        c.circle(cx, cy, rad - 4, (140, 196, 90))
        c.circle(cx, cy, rad - 7, (60, 120, 52))

    # ---- chili oil droplets: glossy red-orange jewels
    for (cx, cy, rad) in [(440, 555, 9), (520, 495, 8), (360, 540, 7),
                          (590, 530, 8), (250, 530, 7)]:
        c.circle(cx, cy, rad, (198, 52, 24))
        c.circle(cx - 2, cy - 3, 3, (255, 120, 70), 0.9)

    # ---- chopsticks lifting glossy noodles (from upper right)
    c.line(700, 150, 520, 430, 16, (122, 74, 32))
    c.line(724, 168, 548, 438, 16, (140, 88, 40))
    c.line(700, 150, 520, 430, 5, (168, 112, 56), 0.8)
    # Noodle strands hanging from the chopstick tips, glistening.
    lift = [
        [(520, 430), (505, 480), (530, 520), (515, 560)],
        [(535, 435), (525, 490), (550, 525), (538, 565)],
        [(548, 440), (545, 495), (565, 530), (555, 568)],
        [(508, 428), (490, 475), (512, 515), (500, 552)],
    ]
    for s in lift:
        c.bezier(s, 10, noodle_dark, 0.95)
        c.bezier([(x - 2, y) for x, y in s], 5, noodle, 0.95)
        c.bezier([(x - 3, y) for x, y in s], 2, noodle_hi, 0.9)

    # ---- steam: soft translucent wisps rising off the hot broth
    # Thin, curvy and faint — steam, not candles. Several passes with
    # tapering alpha so the wisps fade as they rise.
    steam = [
        [(380, 470), (352, 410), (392, 350), (368, 285)],
        [(450, 460), (474, 395), (438, 330), (464, 268)],
        [(520, 465), (544, 400), (508, 340), (534, 280)],
        [(300, 480), (282, 425), (312, 368), (292, 315)],
    ]
    for s in steam:
        c.bezier(s, 10, (255, 250, 240), 0.10)
        c.bezier(s, 6, (255, 252, 245), 0.16)
        # brighter, thinner core low down, fading upward
        c.bezier([s[0], s[1], s[2]], 4, (255, 255, 250), 0.20)

    # ---- final light: warm rim light on the bowl's left edge
    c.ellipse(150, 590, 26, 110, (255, 220, 160), 0.18)
    c.ellipse(450, 470, 300, 60, (255, 235, 190), 0.10)

    return c


def main():
    out_dir = os.environ.get("OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    canvas = draw()
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path, canvas)
    print(f"wrote {path} {canvas.w}x{canvas.h} {size} bytes")


if __name__ == "__main__":
    main()
