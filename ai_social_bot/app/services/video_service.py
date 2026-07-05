import math
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from ai_social_bot.app.services.image_service import _choose_font_path, _draw_heart, _load_font, _wrap_by_pixels


VIDEO_SIZE = (1080, 1920)
FPS = 24


def _text_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: ImageFont.ImageFont,
    y: int,
    fill: tuple[int, int, int],
    line_gap: int,
) -> int:
    width, _ = VIDEO_SIZE
    for line in lines:
        line_width, line_height = _text_bbox(draw, line, font)
        x = int((width - line_width) / 2)
        draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height + line_gap
    return y


def _create_voice_wav(text: str, out_path: Path) -> None:
    text_path = out_path.with_suffix('.txt')
    text_path.write_text(text, encoding='utf-8')
    command = (
        "Add-Type -AssemblyName System.Speech; "
        "$text = Get-Content -LiteralPath '{text_path}' -Raw; "
        "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$synth.SelectVoice('Microsoft Zira Desktop'); "
        "$synth.Rate = -1; "
        "$synth.Volume = 100; "
        "$synth.SetOutputToWaveFile('{out_path}'); "
        "$synth.Speak($text); "
        "$synth.Dispose();"
    ).format(text_path=str(text_path), out_path=str(out_path))
    subprocess.run(['powershell', '-NoProfile', '-Command', command], check=True)


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), 'rb') as wav:
        return wav.getnframes() / wav.getframerate()


def _create_music_wav(out_path: Path, duration: float, sample_rate: int = 44100) -> None:
    total = int(duration * sample_rate)
    t = np.linspace(0, duration, total, endpoint=False)
    envelope = np.minimum(1.0, np.minimum(t / 2.0, (duration - t) / 2.0))
    tones = (
        0.18 * np.sin(2 * math.pi * 220 * t)
        + 0.12 * np.sin(2 * math.pi * 277.18 * t)
        + 0.10 * np.sin(2 * math.pi * 329.63 * t)
    )
    shimmer = 0.035 * np.sin(2 * math.pi * 880 * t) * (0.5 + 0.5 * np.sin(2 * math.pi * 0.18 * t))
    audio = (tones + shimmer) * envelope * 0.32
    pcm = np.int16(np.clip(audio, -1, 1) * 32767)
    with wave.open(str(out_path), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())


def _render_frame(
    background: Image.Image,
    quote: str,
    signature: str,
    explanation: str,
    progress: float,
    font_path: str | None,
) -> Image.Image:
    width, height = VIDEO_SIZE
    frame = background.copy().convert('RGBA')
    overlay = Image.new('RGBA', VIDEO_SIZE, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    for y in range(height):
        distance = abs(y - height / 2) / (height / 2)
        alpha = int(70 + 120 * max(0, 1 - distance))
        draw_overlay.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
    frame = Image.alpha_composite(frame, overlay)
    draw = ImageDraw.Draw(frame)

    quote_font = _load_font(92, font_path)
    explanation_font = _load_font(44, font_path)
    signature_font = _load_font(42, font_path)
    quote_lines = _wrap_by_pixels(draw, quote, quote_font, width - 140)
    explanation_lines = _wrap_by_pixels(draw, explanation, explanation_font, width - 170)

    fade = int(255 * min(1, progress / 0.18, (1 - progress) / 0.12))
    fill = (255, 255, 255, fade)
    soft_fill = (235, 245, 240, fade)

    y = 500
    y = _draw_centered_text(draw, quote_lines, quote_font, y, fill, 22)

    signature_text = signature.replace('❤️', '').strip()
    sig_width, sig_height = _text_bbox(draw, signature_text, signature_font)
    heart_size = 32
    sig_x = int((width - sig_width - 48) / 2)
    sig_y = y + 38
    draw.text((sig_x + 2, sig_y + 2), signature_text, font=signature_font, fill=(0, 0, 0, fade))
    draw.text((sig_x, sig_y), signature_text, font=signature_font, fill=soft_fill)
    _draw_heart(draw, sig_x + sig_width + 18, sig_y + int((sig_height - heart_size) / 2), heart_size, soft_fill)

    y = 1230
    _draw_centered_text(draw, explanation_lines[:4], explanation_font, y, soft_fill, 14)
    return frame.convert('RGB')


def create_quote_video(
    quote: str,
    explanation: str,
    background_path: str,
    out_path: str,
) -> str:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    work_dir = out.parent / f'{out.stem}_work'
    work_dir.mkdir(parents=True, exist_ok=True)

    signature = 'Krishna.....❤️'
    main_quote = quote.replace(signature, '').strip()
    narration = f'{main_quote}. {explanation}'
    voice_wav = work_dir / 'voice.wav'
    music_wav = work_dir / 'music.wav'
    mixed_wav = work_dir / 'mixed.wav'
    silent_mp4 = work_dir / 'silent.mp4'

    _create_voice_wav(narration, voice_wav)
    duration = max(12.0, _wav_duration(voice_wav) + 2.0)
    _create_music_wav(music_wav, duration)

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    background = Image.open(background_path).convert('RGB')
    background = ImageOps.fit(background, VIDEO_SIZE, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    font_path = _choose_font_path('mindfulness', True)

    frame_pattern = work_dir / 'frame_%04d.jpg'
    total_frames = int(duration * FPS)
    for index in range(total_frames):
        progress = index / max(1, total_frames - 1)
        frame = _render_frame(background, main_quote, signature, explanation, progress, font_path)
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
        '-i', str(voice_wav),
        '-i', str(music_wav),
        '-filter_complex', '[0:a]volume=1.0[a0];[1:a]volume=0.18[a1];[a0][a1]amix=inputs=2:duration=longest',
        str(mixed_wav),
    ], check=True)
    subprocess.run([
        ffmpeg,
        '-y',
        '-i', str(silent_mp4),
        '-i', str(mixed_wav),
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-shortest',
        str(out),
    ], check=True)
    return str(out)
