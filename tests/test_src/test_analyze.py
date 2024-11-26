import os
from src.receipt_scanner_model import analyze
from PIL import Image
import io

# 現在のスクリプトのディレクトリを取得
current_dir = os.path.dirname(os.path.abspath(__file__))

# 相対パスで画像ファイルを指定
TEST_IMAGE_PATH = os.path.join(current_dir, "../../raw/book-off.png")


def test_get_receipt_detail():
    """レシートの詳細を取得する関数のテスト"""
    image = Image.open(TEST_IMAGE_PATH)
    img_bytes = io.BytesIO()
    image.save(img_bytes, format="JPEG")
    img_bytes = img_bytes.getvalue()
    expected = {
        "store_name": "BOOKOFF 秋葉原駅前店",
        "amount": 990,
        "date": "2024/07/18",
        "category": "娯楽",
    }
    actual = analyze.get_receipt_detail(img_bytes)
    assert expected == actual
