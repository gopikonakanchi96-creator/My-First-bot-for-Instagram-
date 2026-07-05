import random
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from ai_social_bot.app.core.settings import settings


def _font_candidates() -> list[str]:
    return [
        'C:/Windows/Fonts/arialbd.ttf',
        'C:/Windows/Fonts/segoeuib.ttf',
        'C:/Windows/Fonts/calibrib.ttf',
        'C:/Windows/Fonts/georgiab.ttf',
        'C:/Windows/Fonts/trebucbd.ttf',
        'C:/Windows/Fonts/verdanab.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf',
    ]


def _font_candidates_for_theme(theme: str | None, has_nature_background: bool) -> list[str]:
    theme = (theme or '').lower()
    if has_nature_background or theme in {'mindfulness', 'gratitude'}:
        return [
            'C:/Windows/Fonts/georgiab.ttf',
            'C:/Windows/Fonts/cambriaz.ttf',
            'C:/Windows/Fonts/constanb.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf',
        ]
    if theme in {'motivation', 'success'}:
        return [
            'C:/Windows/Fonts/arialbd.ttf',
            'C:/Windows/Fonts/segoeuib.ttf',
            'C:/Windows/Fonts/verdanab.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        ]
    if theme == 'love':
        return [
            'C:/Windows/Fonts/georgiab.ttf',
            'C:/Windows/Fonts/trebucbd.ttf',
            'C:/Windows/Fonts/calibrib.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf',
        ]
    return _font_candidates()


def _choose_font_path(theme: str | None = None, has_nature_background: bool = False) -> str | None:
    candidates = _font_candidates_for_theme(theme, has_nature_background)
    existing = [font_path for font_path in candidates if Path(font_path).exists()]
    if not existing:
        existing = [font_path for font_path in _font_candidates() if Path(font_path).exists()]
    return random.choice(existing) if existing else None


def _load_font(size: int, font_path: str | None = None, theme: str | None = None, has_nature_background: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if font_path and Path(font_path).exists():
        return ImageFont.truetype(font_path, size)
    fallback = _choose_font_path(theme, has_nature_background)
    if fallback:
        return ImageFont.truetype(fallback, size)
    return ImageFont.load_default()


def _split_quote_signature(quote: str) -> tuple[str, str]:
    normalized = quote.replace('\u2764\ufe0f', '\u2665').replace('\u2764', '\u2665').strip()
    marker = 'Krishna'
    index = normalized.rfind(marker)
    if index == -1:
        return normalized, ''
    main_quote = normalized[:index].strip()
    signature = normalized[index:].strip().replace('??', '').strip()
    if '\u2665' not in signature:
        signature = f'{signature} \u2665'.strip()
    return main_quote, signature


def _wrap_by_pixels(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines = []
    current = ''

    for word in words:
        candidate = f'{current} {word}'.strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def _measure_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: ImageFont.ImageFont,
    line_gap: int,
) -> tuple[int, int, list[int]]:
    widths = []
    heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])

    total_height = sum(heights) + max(0, len(lines) - 1) * line_gap
    return max(widths, default=0), total_height, heights


def _fit_quote(
    draw: ImageDraw.ImageDraw,
    quote: str,
    max_width: int,
    max_height: int,
    font_path: str | None,
) -> tuple[ImageFont.ImageFont, list[str], int, list[int], int]:
    for size in range(106, 54, -2):
        font = _load_font(size, font_path)
        line_gap = max(14, int(size * 0.2))
        lines = _wrap_by_pixels(draw, quote, font, max_width)
        line_width, total_height, heights = _measure_lines(draw, lines, font, line_gap)
        if line_width <= max_width and total_height <= max_height:
            return font, lines, line_gap, heights, size

    size = 54
    font = _load_font(size, font_path)
    line_gap = 14
    lines = _wrap_by_pixels(draw, quote, font, max_width)
    _, _, heights = _measure_lines(draw, lines, font, line_gap)
    return font, lines, line_gap, heights, size


def _draw_centered_line(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    font: ImageFont.ImageFont,
    width: int,
    fill: tuple[int, int, int],
    shadow: bool = True,
) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = int((width - text_width) / 2)
    if shadow:
        draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0))
    draw.text((x, y), text, font=font, fill=fill)
    return text_height


def _draw_heart(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, fill: tuple[int, int, int]) -> None:
    raw_points = []
    for step in range(72):
        t = math.tau * step / 72
        px = 16 * math.sin(t) ** 3
        py = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        raw_points.append((px, py))

    min_x = min(point[0] for point in raw_points)
    max_x = max(point[0] for point in raw_points)
    min_y = min(point[1] for point in raw_points)
    max_y = max(point[1] for point in raw_points)
    scale = size / max(max_x - min_x, max_y - min_y)
    points = [
        (
            int(x + (point[0] - min_x) * scale),
            int(y + (point[1] - min_y) * scale),
        )
        for point in raw_points
    ]
    draw.polygon(points, fill=fill)


def _draw_signature(
    draw: ImageDraw.ImageDraw,
    signature: str,
    y: int,
    font: ImageFont.ImageFont,
    width: int,
    heart_size: int,
) -> int:
    text = signature.replace('\u2665', '').strip()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    gap = 14
    total_width = text_width + gap + heart_size
    x = int((width - total_width) / 2)
    fill = (238, 248, 246)

    draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0))
    draw.text((x, y), text, font=font, fill=fill)
    heart_y = y + max(0, int((text_height - heart_size) / 2))
    _draw_heart(draw, x + text_width + gap + 2, heart_y + 2, heart_size, (0, 0, 0))
    _draw_heart(draw, x + text_width + gap, heart_y, heart_size, fill)
    return max(text_height, heart_size)


def _fit_single_line_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_size: int,
    min_size: int,
    font_path: str | None,
    theme: str | None,
    has_nature_background: bool,
) -> ImageFont.ImageFont:
    for size in range(max_size, min_size - 1, -2):
        font = _load_font(size, font_path, theme, has_nature_background)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
    return _load_font(min_size, font_path, theme, has_nature_background)


def _draw_account_links(
    draw: ImageDraw.ImageDraw,
    account_links: dict | None,
    width: int,
    height: int,
    font_path: str | None,
    theme: str | None,
    has_nature_background: bool,
    middle_y: int,
) -> None:
    if not account_links:
        return

    instagram_username = account_links.get('instagram_username')
    facebook_name = account_links.get('facebook_name')
    footer_lines = [
        line
        for line in [
            f'@{instagram_username}' if instagram_username else None,
            f'Facebook: {facebook_name}' if facebook_name else None,
        ]
        if line
    ]

    if not footer_lines:
        return

    footer_font = _fit_single_line_font(
        draw,
        max(footer_lines, key=len),
        width - 150,
        30,
        20,
        font_path,
        theme,
        has_nature_background,
    )
    line_height = max(draw.textbbox((0, 0), line, font=footer_font)[3] for line in footer_lines)
    y = height - 118 - (len(footer_lines) - 1) * (line_height + 10)
    for line in footer_lines:
        drawn_height = _draw_centered_line(draw, line, y, footer_font, width, (240, 248, 245), shadow=True)
        y += drawn_height + 10


def _quote_backgrounds() -> list[Path]:
    if not settings.USE_NATURE_BACKGROUNDS:
        return []
    bg_dir = Path(settings.NATURE_BACKGROUND_DIR)
    if not bg_dir.exists():
        return []
    backgrounds = list(bg_dir.glob('nature_background_*.*'))
    backgrounds.extend(bg_dir.glob('quote_background_*.*'))
    return sorted(backgrounds)


def _choose_background(backgrounds: list[Path]) -> Path:
    state_path = Path('ai_social_bot/assets/.last_background')
    last_name = state_path.read_text(encoding='utf-8').strip() if state_path.exists() else ''
    choices = [path for path in backgrounds if path.name != last_name]
    selected = random.choice(choices or backgrounds)
    state_path.write_text(selected.name, encoding='utf-8')
    return selected


def _draw_overlay(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    for y in range(height):
        distance = abs(y - height / 2) / (height / 2)
        alpha = int(95 + 95 * max(0, 1 - distance))
        draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))


def create_quote_image(
    quote: str,
    author: str,
    filename: str,
    logo_path: str = None,
    palette: tuple = None,
    theme: str | None = None,
    background_path: str | None = None,
    account_links: dict | None = None,
) -> str:
    """Create a readable 1080x1350 quote image with varied font, centered quote, and smaller signature."""
    main_quote, signature = _split_quote_signature(quote)
    width, height = 1080, 1350
    out_dir = Path('ai_social_bot/assets')
    out_dir.mkdir(parents=True, exist_ok=True)

    backgrounds = _quote_backgrounds()
    has_nature_background = bool(backgrounds)
    if background_path:
        img = Image.open(background_path).convert('RGB')
        has_nature_background = True
    elif backgrounds:
        img = Image.open(_choose_background(backgrounds)).convert('RGB')
    else:
        img = None

    if img:
        img = ImageOps.fit(img, (width, height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        _draw_overlay(ImageDraw.Draw(overlay), width, height)
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    else:
        if not palette:
            palette = random.choice([
                ((18, 48, 64), (108, 188, 196)),
                ((55, 35, 82), (222, 125, 98)),
                ((20, 75, 50), (210, 190, 120)),
                ((68, 32, 48), (205, 92, 135)),
                ((35, 42, 58), (150, 175, 165)),
            ])

        img = Image.new('RGB', (width, height), color=palette[0])
        draw = ImageDraw.Draw(img)

        r1, g1, b1 = palette[0]
        r2, g2, b2 = palette[1]
        for i in range(height):
            t = i / (height - 1)
            r = int(r1 * (1 - t) + r2 * t)
            g = int(g1 * (1 - t) + g2 * t)
            b = int(b1 * (1 - t) + b2 * t)
            draw.line([(0, i), (width, i)], fill=(r, g, b))

    draw = ImageDraw.Draw(img)

    font_path = _choose_font_path(theme, has_nature_background)
    max_text_width = width - 140
    max_quote_height = 560
    font, lines, line_gap, line_heights, quote_size = _fit_quote(
        draw,
        main_quote,
        max_text_width,
        max_quote_height,
        font_path,
    )
    _, quote_height, _ = _measure_lines(draw, lines, font, line_gap)

    signature_font = _load_font(max(34, min(52, int(quote_size * 0.42))), font_path, theme, has_nature_background)
    heart_size = max(26, min(40, int(quote_size * 0.32)))
    signature_height = 0
    if signature:
        signature_bbox = draw.textbbox((0, 0), signature.replace('\u2665', '').strip(), font=signature_font)
        signature_height = signature_bbox[3] - signature_bbox[1]
        signature_height = max(signature_height, heart_size)

    signature_gap = 42 if signature else 0
    group_height = quote_height + signature_gap + signature_height
    y = int((height - group_height) / 2)

    for index, line in enumerate(lines):
        line_height = _draw_centered_line(draw, line, y, font, width, (255, 255, 255))
        y += line_height + line_gap

    if signature:
        y += signature_gap
        signature_drawn_height = _draw_signature(draw, signature, y, signature_font, width, heart_size)
        y += signature_drawn_height

    _draw_account_links(
        draw,
        account_links,
        width,
        height,
        font_path,
        theme,
        has_nature_background,
        middle_y=min(y + 44, height - 250),
    )

    if author:
        author_font = _load_font(40, font_path, theme, has_nature_background)
        _draw_centered_line(draw, author.strip(), 72, author_font, width, (235, 245, 248), shadow=False)

    if logo_path and Path(logo_path).exists():
        logo = Image.open(logo_path).convert('RGBA')
        logo.thumbnail((120, 120))
        img.paste(logo, (width - 145, height - 145), logo)

    out = out_dir / filename
    img.save(out, format='JPEG', quality=95)
    return str(out)
