import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


WIDTH = 1080
HEIGHT = 1350
OUT_DIR = Path('ai_social_bot/assets')


PALETTES = [
    ((12, 28, 54), (244, 178, 104), (31, 88, 89)),
    ((18, 48, 42), (214, 178, 96), (58, 104, 78)),
    ((42, 30, 66), (220, 134, 132), (82, 70, 116)),
    ((8, 35, 58), (120, 190, 214), (245, 214, 150)),
    ((43, 39, 34), (222, 174, 105), (122, 88, 58)),
    ((20, 26, 46), (188, 202, 224), (54, 82, 130)),
    ((28, 56, 68), (198, 226, 214), (70, 122, 116)),
    ((56, 35, 48), (232, 166, 150), (108, 62, 84)),
]


def blend(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def radial_light(img: Image.Image, color: tuple[int, int, int], center: tuple[int, int], radius: int, power: float) -> None:
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    pix = overlay.load()
    cx, cy = center
    for y in range(HEIGHT):
        for x in range(WIDTH):
            d = math.hypot(x - cx, y - cy) / radius
            if d < 1:
                alpha = int((1 - d) ** power * 150)
                pix[x, y] = (*color, alpha)
    img.alpha_composite(overlay)


def gradient_background(top: tuple[int, int, int], mid: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    img = Image.new('RGBA', (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        if t < 0.55:
            c = blend(top, mid, t / 0.55)
        else:
            c = blend(mid, bottom, (t - 0.55) / 0.45)
        draw.line([(0, y), (WIDTH, y)], fill=(*c, 255))
    return img


def draw_mountains(draw: ImageDraw.ImageDraw, rng: random.Random, base_y: int, color: tuple[int, int, int], layers: int) -> None:
    for layer in range(layers):
        y = base_y + layer * 90
        points = [(0, HEIGHT)]
        x = -80
        while x < WIDTH + 100:
            peak_y = y - rng.randint(120, 260) + layer * 45
            points.append((x, peak_y))
            x += rng.randint(140, 240)
        points.append((WIDTH, HEIGHT))
        shade = tuple(max(0, c - layer * 24) for c in color)
        draw.polygon(points, fill=(*shade, 175 - layer * 25))


def draw_forest(draw: ImageDraw.ImageDraw, rng: random.Random, color: tuple[int, int, int]) -> None:
    for _ in range(95):
        x = rng.randint(-80, WIDTH + 80)
        h = rng.randint(110, 340)
        y = HEIGHT - rng.randint(40, 330)
        w = rng.randint(36, 86)
        shade = tuple(max(0, min(255, c + rng.randint(-18, 18))) for c in color)
        draw.polygon([(x, y - h), (x - w, y), (x + w, y)], fill=(*shade, rng.randint(75, 135)))
        draw.rectangle((x - 4, y - h // 4, x + 4, y + 12), fill=(*shade, rng.randint(70, 120)))


def draw_particles(draw: ImageDraw.ImageDraw, rng: random.Random, color: tuple[int, int, int], count: int) -> None:
    for _ in range(count):
        x = rng.randint(0, WIDTH)
        y = rng.randint(0, HEIGHT)
        r = rng.choice([1, 1, 2, 2, 3])
        a = rng.randint(28, 95)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(*color, a))


def draw_waves(draw: ImageDraw.ImageDraw, rng: random.Random, color: tuple[int, int, int]) -> None:
    for row in range(18):
        y = 790 + row * 24
        points = []
        for x in range(-20, WIDTH + 30, 18):
            points.append((x, y + int(math.sin(x / 55 + row) * 8)))
        draw.line(points, fill=(*color, max(18, 78 - row * 3)), width=rng.randint(2, 4))


def draw_desert(draw: ImageDraw.ImageDraw, rng: random.Random, color: tuple[int, int, int]) -> None:
    for row in range(12):
        y = 800 + row * 55
        points = [(0, HEIGHT), (0, y)]
        for x in range(0, WIDTH + 80, 80):
            points.append((x, y + int(math.sin(x / 115 + row * 0.9) * (22 + row * 4))))
        points.extend([(WIDTH, HEIGHT)])
        shade = tuple(max(0, min(255, c + row * 7)) for c in color)
        draw.polygon(points, fill=(*shade, 54))


def draw_branches(draw: ImageDraw.ImageDraw, rng: random.Random, color: tuple[int, int, int]) -> None:
    for _ in range(18):
        start_x = rng.choice([rng.randint(-80, 80), rng.randint(WIDTH - 80, WIDTH + 80)])
        start_y = rng.randint(0, 650)
        length = rng.randint(170, 420)
        angle = rng.uniform(0.15, 0.95) if start_x < WIDTH / 2 else rng.uniform(2.2, 2.95)
        end_x = start_x + int(math.cos(angle) * length)
        end_y = start_y + int(math.sin(angle) * length)
        draw.line((start_x, start_y, end_x, end_y), fill=(*color, rng.randint(85, 135)), width=rng.randint(4, 9))
        for __ in range(rng.randint(10, 24)):
            lx = start_x + int((end_x - start_x) * rng.random())
            ly = start_y + int((end_y - start_y) * rng.random())
            r = rng.randint(7, 17)
            draw.ellipse((lx - r, ly - r, lx + r, ly + r), fill=(*color, rng.randint(60, 120)))


def make_background(index: int, seed: int) -> Image.Image:
    rng = random.Random(seed)
    top, mid, bottom = PALETTES[index % len(PALETTES)]
    img = gradient_background(top, mid, bottom)
    draw = ImageDraw.Draw(img, 'RGBA')

    mode = index % 8
    if mode in {0, 5}:
        radial_light(img, (255, 224, 160), (rng.randint(420, 720), rng.randint(190, 450)), rng.randint(420, 720), 2.1)
        draw_mountains(draw, rng, rng.randint(760, 920), bottom, 3)
    if mode in {1, 6}:
        radial_light(img, (230, 250, 220), (rng.randint(350, 780), rng.randint(230, 520)), rng.randint(500, 760), 2.4)
        draw_forest(draw, rng, bottom)
        draw_branches(draw, rng, top)
    if mode == 2:
        radial_light(img, (255, 185, 185), (WIDTH // 2, 300), 650, 2.6)
        draw_particles(draw, rng, (255, 220, 220), 280)
    if mode == 3:
        radial_light(img, (170, 230, 255), (WIDTH // 2, 330), 700, 2.5)
        draw_waves(draw, rng, (225, 245, 255))
    if mode == 4:
        radial_light(img, (255, 214, 150), (WIDTH // 2, 360), 760, 2.2)
        draw_desert(draw, rng, bottom)
    if mode == 7:
        radial_light(img, (255, 200, 210), (rng.randint(260, 820), rng.randint(240, 480)), 620, 2.2)
        draw_particles(draw, rng, (255, 226, 210), 220)
        draw_branches(draw, rng, bottom)

    vignette = Image.new('RGBA', img.size, (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    for y in range(HEIGHT):
        distance = abs(y - HEIGHT / 2) / (HEIGHT / 2)
        alpha = int(40 + 110 * distance)
        vdraw.line([(0, y), (WIDTH, y)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, vignette)

    texture = Image.effect_noise((WIDTH, HEIGHT), rng.uniform(10, 22)).convert('L')
    texture = texture.point(lambda p: int(p * 0.18))
    img.putalpha(255)
    img = Image.composite(Image.new('RGBA', img.size, (255, 255, 255, 22)), img, texture)
    return img.convert('RGB').filter(ImageFilter.SMOOTH_MORE)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for index in range(1, 25):
        image = make_background(index, 7351 + index * 97)
        image.save(OUT_DIR / f'quote_background_generated_{index:02d}.png', quality=95)


if __name__ == '__main__':
    main()
