from PIL import Image

def save_image_from_base64(b64str: str, out_path: str) -> str:
    import base64
    data = base64.b64decode(b64str)
    with open(out_path, 'wb') as f:
        f.write(data)
    return out_path
