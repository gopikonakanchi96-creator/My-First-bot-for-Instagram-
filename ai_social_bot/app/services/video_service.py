import math
import random
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from ai_social_bot.app.prompts.prompts import QUOTE_SUFFIX
from ai_social_bot.app.services.image_service import (
    _choose_background,
    _choose_font_path,
    _draw_heart,
    _fit_single_line_font,
    _load_font,
    _quote_backgrounds,
    _split_quote_signature,
    _wrap_by_pixels,
)


VIDEO_SIZE = (1080, 1920)
FPS = 24
VIDEO_STYLES = [
    {
        'name': 'center_rise',
        'reveal': 'word',
        'quote_y': 560,
        'quote_size': 86,
        'line_gap': 22,
        'signature_gap': 42,
        'motion': 'rise',
        'accent': 'none',
    },
    {
        'name': 'calm_lines',
        'reveal': 'line',
        'quote_y': 500,
        'quote_size': 78,
        'line_gap': 26,
        'signature_gap': 50,
        'motion': 'still',
        'accent': 'top_bottom',
    },
    {
        'name': 'bold_steps',
        'reveal': 'chunk',
        'quote_y': 620,
        'quote_size': 92,
        'line_gap': 20,
        'signature_gap': 36,
        'motion': 'push',
        'accent': 'left_bar',
    },
    {
        'name': 'quiet_type',
        'reveal': 'type',
        'quote_y': 540,
        'quote_size': 74,
        'line_gap': 24,
        'signature_gap': 46,
        'motion': 'float',
        'accent': 'soft_frame',
    },
]

THEME_ACCENTS = {
    'love': (246, 178, 190, 170),
    'motivation': (248, 202, 96, 170),
    'success': (185, 226, 150, 170),
    'mindfulness': (168, 220, 214, 170),
    'gratitude': (236, 196, 126, 170),
    'inspiration': (180, 220, 236, 170),
}


def _text_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: ImageFont.ImageFont,
    y: int,
    fill: tuple[int, int, int, int],
    line_gap: int,
) -> int:
    width, _ = VIDEO_SIZE
    for line in lines:
        line_width, line_height = _text_bbox(draw, line, font)
        x = int((width - line_width) / 2)
        draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, fill[3]))
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height + line_gap
    return y


def _choose_video_style(theme: str | None) -> dict:
    style = random.choice(VIDEO_STYLES).copy()
    style['accent_color'] = THEME_ACCENTS.get((theme or '').lower(), THEME_ACCENTS['inspiration'])
    return style


def _visible_quote(quote: str, progress: float, style: dict) -> str:
    words = quote.split()
    if not words:
        return ''

    reveal_progress = min(1, progress / 0.78)
    if style['reveal'] == 'type':
        visible_chars = max(1, math.ceil(len(quote) * reveal_progress))
        return quote[:visible_chars].rstrip()
    if style['reveal'] == 'chunk':
        chunk_size = 2
        visible_chunks = max(1, math.ceil((len(words) / chunk_size) * reveal_progress))
        return ' '.join(words[:visible_chunks * chunk_size])
    if style['reveal'] == 'line':
        visible_count = max(1, math.ceil(len(words) * reveal_progress))
        return ' '.join(words[:visible_count])

    visible_count = max(1, math.ceil(len(words) * reveal_progress))
    return ' '.join(words[:visible_count])


def _motion_offset(progress: float, style: dict) -> int:
    if style['motion'] == 'rise':
        return int((1 - min(1, progress / 0.3)) * 42)
    if style['motion'] == 'push':
        return int(math.sin(min(1, progress) * math.pi) * -18)
    if style['motion'] == 'float':
        return int(math.sin(progress * math.tau) * 10)
    return 0


def _draw_design_accent(
    draw: ImageDraw.ImageDraw,
    style: dict,
    progress: float,
) -> None:
    width, height = VIDEO_SIZE
    alpha = int(style['accent_color'][3] * min(1, progress / 0.2, (1 - progress) / 0.12))
    color = (*style['accent_color'][:3], alpha)

    if style['accent'] == 'top_bottom':
        draw.line([(170, 270), (width - 170, 270)], fill=color, width=5)
        draw.line([(170, height - 330), (width - 170, height - 330)], fill=color, width=5)
    elif style['accent'] == 'left_bar':
        draw.rounded_rectangle((88, 430, 104, 1180), radius=8, fill=color)
    elif style['accent'] == 'soft_frame':
        draw.rounded_rectangle((78, 360, width - 78, 1260), radius=22, outline=color, width=3)


def _theme_tones(theme: str | None) -> tuple[float, float, float]:
    tones_by_theme = {
        'love': (196.0, 246.94, 329.63),
        'motivation': (220.0, 293.66, 440.0),
        'success': (246.94, 329.63, 493.88),
        'mindfulness': (174.61, 220.0, 261.63),
        'gratitude': (196.0, 261.63, 392.0),
        'inspiration': (220.0, 277.18, 329.63),
    }
    return tones_by_theme.get((theme or '').lower(), tones_by_theme['inspiration'])


def _create_music_wav(out_path: Path, duration: float, theme: str | None, sample_rate: int = 44100) -> None:
    total = int(duration * sample_rate)
    t = np.linspace(0, duration, total, endpoint=False)
    envelope = np.minimum(1.0, np.minimum(t / 2.0, (duration - t) / 2.0))
    low, mid, high = _theme_tones(theme)
    tones = (
        0.18 * np.sin(2 * math.pi * low * t)
        + 0.12 * np.sin(2 * math.pi * mid * t)
        + 0.10 * np.sin(2 * math.pi * high * t)
    )
    shimmer = 0.035 * np.sin(2 * math.pi * high * 2 * t) * (0.5 + 0.5 * np.sin(2 * math.pi * 0.18 * t))
    audio = (tones + shimmer) * envelope * 0.32
    pcm = np.int16(np.clip(audio, -1, 1) * 32767)
    with wave.open(str(out_path), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())


def _draw_signature(
    draw: ImageDraw.ImageDraw,
    signature: str,
    y: int,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
) -> None:
    width, _ = VIDEO_SIZE
    signature_text = signature.replace('\u2665', '').replace('❤️', '').strip()
    sig_width, sig_height = _text_bbox(draw, signature_text, font)
    heart_size = 34
    total_width = sig_width + 18 + heart_size
    x = int((width - total_width) / 2)
    draw.text((x + 2, y + 2), signature_text, font=font, fill=(0, 0, 0, fill[3]))
    draw.text((x, y), signature_text, font=font, fill=fill)
    heart_y = y + int((sig_height - heart_size) / 2)
    _draw_heart(draw, x + sig_width + 18, heart_y, heart_size, fill)


def _draw_footer(
    draw: ImageDraw.ImageDraw,
    account_links: dict | None,
    font_path: str | None,
    theme: str | None,
    fill: tuple[int, int, int, int],
) -> None:
    if not account_links:
        return

    width, height = VIDEO_SIZE
    footer_lines = []
    instagram_username = account_links.get('instagram_username')
    facebook_name = account_links.get('facebook_name')
    if instagram_username:
        footer_lines.append(f'@{instagram_username}')
    if facebook_name:
        footer_lines.append(f'Facebook: {facebook_name}')
    if not footer_lines:
        return

    footer_font = _fit_single_line_font(
        draw,
        max(footer_lines, key=len),
        width - 150,
        36,
        24,
        font_path,
        theme,
        True,
    )
    y = height - 220
    for line in footer_lines:
        line_width, line_height = _text_bbox(draw, line, footer_font)
        x = int((width - line_width) / 2)
        draw.text((x + 2, y + 2), line, font=footer_font, fill=(0, 0, 0, fill[3]))
        draw.text((x, y), line, font=footer_font, fill=fill)
        y += line_height + 12


def _render_frame(
    background: Image.Image,
    quote: str,
    signature: str,
    account_links: dict | None,
    progress: float,
    font_path: str | None,
    theme: str | None,
    style: dict,
) -> Image.Image:
    width, height = VIDEO_SIZE
    frame = background.copy().convert('RGBA')
    overlay = Image.new('RGBA', VIDEO_SIZE, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    for y in range(height):
        distance = abs(y - height / 2) / (height / 2)
        alpha = int(75 + 120 * max(0, 1 - distance))
        draw_overlay.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
    frame = Image.alpha_composite(frame, overlay)
    draw = ImageDraw.Draw(frame)
    _draw_design_accent(draw, style, progress)

    quote_font = _load_font(style['quote_size'], font_path, theme, True)
    signature_font = _load_font(42, font_path, theme, True)
    fade = int(255 * min(1, progress / 0.12, (1 - progress) / 0.08))
    fill = (255, 255, 255, fade)
    soft_fill = (235, 245, 240, fade)

    visible_quote = _visible_quote(quote, progress, style)
    quote_lines = _wrap_by_pixels(draw, visible_quote, quote_font, width - 140)
    y = style['quote_y'] + _motion_offset(progress, style)
    y = _draw_centered_text(draw, quote_lines, quote_font, y, fill, style['line_gap'])
    _draw_signature(draw, signature, y + style['signature_gap'], signature_font, soft_fill)

    _draw_footer(draw, account_links, font_path, theme, soft_fill)
    return frame.convert('RGB')


def create_quote_video(
    quote: str,
    explanation: str,
    out_path: str,
    background_path: str | None = None,
    theme: str | None = None,
    account_links: dict | None = None,
) -> str:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    work_dir = out.parent / f'{out.stem}_work'
    work_dir.mkdir(parents=True, exist_ok=True)

    main_quote, signature = _split_quote_signature(quote)
    signature = signature or QUOTE_SUFFIX
    music_wav = work_dir / 'music.wav'
    silent_mp4 = work_dir / 'silent.mp4'

    duration = max(10.0, len(main_quote.split()) * 0.65 + 4.0)
    _create_music_wav(music_wav, duration, theme)

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    if background_path:
        selected_background = Path(background_path)
    else:
        backgrounds = _quote_backgrounds()
        if not backgrounds:
            raise RuntimeError('No quote backgrounds are available for video creation')
        selected_background = _choose_background(backgrounds)

    background = Image.open(selected_background).convert('RGB')
    background = ImageOps.fit(background, VIDEO_SIZE, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    font_path = _choose_font_path(theme, True)
    style = _choose_video_style(theme)

    total_frames = int(duration * FPS)
    frame_pattern = work_dir / 'frame_%04d.jpg'
    for index in range(total_frames):
        progress = index / max(1, total_frames - 1)
        frame = _render_frame(
            background,
            main_quote,
            signature,
            account_links,
            progress,
            font_path,
            theme,
            style,
        )
        frame.save(work_dir / f'frame_{index:04d}.jpg', quality=92)

    subprocess.run([
        ffmpeg,
        '-y',
        '-framerate', str(FPS),
        '-i', str(frame_pattern),
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-r', str(FPS),
        str(silent_mp4),
    ], check=True)
    subprocess.run([
        ffmpeg,
        '-y',
        '-i', str(silent_mp4),
        '-i', str(music_wav),
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-shortest',
        str(out),
    ], check=True)
    return str(out)
