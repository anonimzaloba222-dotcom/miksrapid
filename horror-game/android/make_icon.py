"""Рисует иконку приложения (лицо в шляпе с красными глазами) во всех плотностях."""
import os, sys
from PIL import Image, ImageDraw, ImageFilter

S = 512
img = Image.new('RGBA', (S, S))
d = ImageDraw.Draw(img)
for r in range(S // 2, 0, -2):  # тёмно-красный радиальный фон
    k = r / (S / 2)
    d.ellipse([S/2 - r*1.42, S/2 - r*1.42, S/2 + r*1.42, S/2 + r*1.42], fill=(int(70 * (1 - k) + 8), 0, 0, 255))
d.ellipse([136, 170, 376, 470], fill=(205, 198, 182))            # лицо
d.rectangle([60, 160, 452, 196], fill=(5, 5, 5))                  # поля шляпы
d.rectangle([150, 30, 362, 170], fill=(5, 5, 5))                  # тулья
d.ellipse([170, 240, 240, 330], fill=(0, 0, 0))                   # глазницы
d.ellipse([272, 240, 342, 330], fill=(0, 0, 0))
d.ellipse([228, 360, 284, 450], fill=(0, 0, 0))                   # рот
glow = Image.new('RGBA', (S, S)); g = ImageDraw.Draw(glow)
for cx in (205, 307):
    g.ellipse([cx - 22, 268, cx + 22, 312], fill=(255, 0, 0, 255))
img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(10)))
d = ImageDraw.Draw(img)
for cx in (205, 307):
    d.ellipse([cx - 10, 280, cx + 10, 300], fill=(255, 60, 60))

res = sys.argv[1]
for name, size in [('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)]:
    os.makedirs(f'{res}/mipmap-{name}', exist_ok=True)
    img.resize((size, size), Image.LANCZOS).save(f'{res}/mipmap-{name}/ic_launcher.png')
