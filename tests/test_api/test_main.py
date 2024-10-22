from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

TEST_IMAGE_PATH = "/Users/ayumu/my-projects/receipt-scanner-model/raw/ok.jpeg"


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
