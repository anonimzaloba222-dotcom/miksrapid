"""Иконка: олений череп с рогами и светящимися глазами на фоне ночного леса."""
import os, sys, math, random
from PIL import Image, ImageDraw, ImageFilter
random.seed(7)
S = 512
img = Image.new('RGBA', (S, S), (8, 10, 16, 255))
d = ImageDraw.Draw(img)
for r in range(S, 0, -4):  # тёмно-синее небо
    k = r / S
    d.ellipse([S / 2 - r, S * 0.3 - r, S / 2 + r, S * 0.3 + r], fill=(int(10 + 25 * (1 - k)), int(14 + 28 * (1 - k)), int(24 + 40 * (1 - k)), 255))
for i in range(14):  # ели
    x = random.randint(-20, S + 20); h = random.randint(120, 260); w = h * 0.38
    d.polygon([(x, S - h), (x - w, S), (x + w, S)], fill=(6, 12, 9, 255))
def antler(x, y, a, ln, wd, depth, sx):
    if depth < 0 or wd < 2: return
    x2, y2 = x + math.cos(a) * ln, y + math.sin(a) * ln
    d.line([(x, y), (x2, y2)], fill=(214, 204, 178, 255), width=int(wd))
    antler(x2, y2, a - sx * 0.35, ln * 0.75, wd * 0.72, depth - 1, sx)
    antler(x2, y2, a + sx * 0.55, ln * 0.55, wd * 0.6, depth - 2, sx)
for sx in (-1, 1):
    antler(S / 2 + sx * 40, 200, -math.pi / 2 + sx * 0.75, 95, 16, 4, sx)
d.ellipse([186, 170, 326, 300], fill=(222, 212, 188, 255))          # череп
d.polygon([(206, 270), (306, 270), (282, 420), (230, 420)], fill=(214, 204, 178, 255))  # морда
for sx in (-1, 1):
    d.ellipse([256 + sx * 38 - 22, 214, 256 + sx * 38 + 22, 262], fill=(10, 8, 6, 255))
d.ellipse([244, 388, 254, 402], fill=(30, 20, 15, 255)); d.ellipse([258, 388, 268, 402], fill=(30, 20, 15, 255))
glow = Image.new('RGBA', (S, S)); g = ImageDraw.Draw(glow)
for sx in (-1, 1): g.ellipse([256 + sx * 38 - 14, 228, 256 + sx * 38 + 14, 250], fill=(255, 240, 160, 255))
img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(9)))
d = ImageDraw.Draw(img)
for sx in (-1, 1): d.ellipse([256 + sx * 38 - 6, 234, 256 + sx * 38 + 6, 244], fill=(255, 250, 220, 255))
res = sys.argv[1]
for name, size in [('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)]:
    os.makedirs(f'{res}/mipmap-{name}', exist_ok=True)
    img.resize((size, size), Image.LANCZOS).save(f'{res}/mipmap-{name}/ic_launcher.png')
