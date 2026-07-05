QUOTE_SUFFIX = 'Krishna.....❤️'

QUOTE_PROMPT = '''
You are an assistant that generates a unique inspirational quote and supporting content.
Return a JSON object with fields: title, quote, explanation, cta, hashtags (list of 15), image_prompt, theme
Ensure the quote is unique, readable, 8 to 14 words before the suffix, and MUST end with the exact text: Krishna.....❤️
Do not reuse common quotes or repeat prior wording.
Detect the theme (one of: love, motivation, inspiration, success, mindfulness, gratitude) and include it in the 'theme' field.
Provide 15 relevant hashtags aligned with the detected theme.
'''

IMAGE_PROMPTS = [
    'Minimalist inspirational quote on gradient background, modern typography, high quality, 1080x1350',
    'Luxury black and gold quote card, elegant serif typography, 1080x1350',
    'Blue gradient, glassmorphism, modern typography, 1080x1350',
    'Warm sunrise quote card, clean centered typography, 1080x1350',
    'Deep green and gold inspirational typography post, 1080x1350',
]
