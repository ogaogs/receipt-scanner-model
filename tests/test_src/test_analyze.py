from src.receipt_scanner_model import analyze
from PIL import Image
import io


TEST_IMAGE_PATH = "/Users/ayumu/my-projects/receipt-scanner-model/raw/ok.jpeg"


def test_main():
    image = Image.open(TEST_IMAGE_PATH)
    img_bytes = io.BytesIO()
    image.save(img_bytes, format="JPEG")
    img_bytes = img_bytes.getvalue()
    expected = 1125
    actual = analyze.main(img_bytes)["amount"]
    assert expected == actual


def test_dict_max_empty():
    amount_dict = {}
    expected = 0
    actual = analyze.dict_max(amount_dict)
    assert expected == actual


def test_dict_max():
    amount_dict = {1042: 1, 1: 1, 1125: 2}
    expected = 1125
    actual = analyze.dict_max(amount_dict)
    assert expected == actual


def test_get_most_likely():
    kws_amount_dict = {
        "合計": [1],
        "小計": [1042],
        "計": [1042, 1],
        "言十": [],
        "paypay": [],
        "クレジット": [1125],
        "キャッシュレス": [],
    }
    count_amount_dict = {1042: 2, 1: 2, 1125: 1}
    expected = 1125
    actual = analyze.get_most_likely(kws_amount_dict, count_amount_dict)
    assert expected == actual
