"""src/receipt_scanner_model/scan_receipt.pyは現在使用していない。"""

import os
from src.receipt_scanner_model import scan_receipt
from PIL import Image
import io
import pytest

# 現在のスクリプトのディレクトリを取得
current_dir = os.path.dirname(os.path.abspath(__file__))

# 相対パスで画像ファイルを指定
TEST_IMAGE_PATH = os.path.join(current_dir, "../../raw/ok.jpeg")


@pytest.mark.skip(reason="現在使用していない")
def test_main():
    """
    レシートの合計金額を取得する関数のテスト
    """
    image = Image.open(TEST_IMAGE_PATH)
    img_bytes = io.BytesIO()
    image.save(img_bytes, format="JPEG")
    img_bytes = img_bytes.getvalue()
    expected = 1125
    actual = scan_receipt.scan(img_bytes)["amount"]
    assert expected == actual


@pytest.mark.skip(reason="現在使用していない")
def test_dict_max_empty():
    """
    amount_dictが{}の場合のdict_max関数のテスト
    """
    amount_dict = {}
    expected = 0
    actual = scan_receipt.dict_max(amount_dict)
    assert expected == actual


@pytest.mark.skip(reason="現在使用していない")
def test_dict_max():
    """
    dict_max関数のテスト
    """
    amount_dict = {1042: 1, 1: 1, 1125: 2}
    expected = 1125
    actual = scan_receipt.dict_max(amount_dict)
    assert expected == actual


@pytest.mark.skip(reason="現在使用していない")
def test_get_most_likely():
    """
    get_most_likely関数のテスト
    """
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
    actual = scan_receipt.get_most_likely(kws_amount_dict, count_amount_dict)
    assert expected == actual
