QUOTE_SUFFIX = 'Krishna.....\u2764\ufe0f'

QUOTE_PROMPT = f'''
You are creating one premium social-media quote post for a Facebook and Instagram quote page.
Return only valid JSON with fields: title, quote, explanation, cta, hashtags, image_prompt, theme, style.

Hard rules:
- The quote must be original, readable, emotionally specific, and 8 to 14 words before the suffix.
- The quote MUST end with the exact text: {QUOTE_SUFFIX}
- Do not reuse common quote wording, generic phrases, or prior-sounding lines.
- Do not use these weak/generic phrases: inner light, radiance, journey, embrace, shine bright, true contentment, external validation, positive vibes.
- Do not write therapy-style filler such as "cultivating your inner garden" or "the world awaits your glow".
- Make the quote concrete and fresh: use a clear image, action, or contrast.
- Pick one theme: love, motivation, inspiration, success, mindfulness, gratitude.
- Pick one style: cinematic, editorial, serene, bold, devotional, modern, sunrise, night, nature, minimal.
- The explanation must be 1 short grounded sentence under 24 words, not generic filler.
- The cta must be short and natural, not salesy.
- hashtags must be a JSON list of 15 hashtag strings, each starting with #.
- image_prompt must describe a distinct visual mood, color direction, scene/background idea, and typography style.

Make each post feel like a different creative concept, not a reused template.
'''

IMAGE_PROMPTS = [
    'Cinematic mountain horizon with luminous morning atmosphere, elegant serif typography, 1080x1350',
    'Editorial monochrome quote poster with refined contrast and minimal gold accent, 1080x1350',
    'Modern glass-light composition with teal, coral, and soft white typography, 1080x1350',
    'Peaceful sunrise landscape with airy centered type and warm natural color, 1080x1350',
    'Deep forest and gold devotional mood with classic typography, 1080x1350',
    'Night-sky reflection scene with quiet silver typography and spacious composition, 1080x1350',
    'Clean botanical background with earth tones, soft grain, and calm serif typography, 1080x1350',
    'Bold success poster with structured layout, high contrast, and confident sans typography, 1080x1350',
]
