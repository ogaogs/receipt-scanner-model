import os
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


# 現在のスクリプトのディレクトリを取得
current_dir = os.path.dirname(os.path.abspath(__file__))

# 相対パスで画像ファイルを指定
TEST_IMAGE_PATH = os.path.join(current_dir, "../../raw/ok.jpeg")


def test_root():
    """
    APIのバージョンを確認するテスト
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"version": "0.1.0"}


def test_post_receipt_analyze():
    """
    レシートのfpを確認するテスト
    """
    response = client.post(
        "/scan-receipt",
        files={"file": open(TEST_IMAGE_PATH, "rb")},
    )
    assert response.status_code == 200
    assert response.json() == {"total": 1125}
