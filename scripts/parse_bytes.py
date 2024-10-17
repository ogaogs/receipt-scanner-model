from PIL import Image
import io


def imgstr_to_bytes(image_path) -> bytes:
    image = Image.open(image_path)
    img_bytes = io.BytesIO()
    image.save(img_bytes, format="JPEG")
    return img_bytes.getvalue()
