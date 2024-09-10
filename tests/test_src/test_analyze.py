from src.receipt_scanner_model import analyze
from PIL import Image
import io


TEST_IMAGE_PATH = "/Users/ayumu/my-projects/receipt-scanner-model/raw/ok.jpeg"


def test_main():
    image = Image.open(TEST_IMAGE_PATH)
    img_bytes = io.BytesIO()
    image.save(img_bytes, format="JPEG")
    img_bytes = img_bytes.getvalue()
    assert isinstance(analyze.main(img_bytes), int)
