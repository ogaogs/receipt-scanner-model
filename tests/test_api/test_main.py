from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


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
        "/receipt-analyze",
        json={
            "file": "/Users/ayumu/my-projects/receipt-scanner-model/raw/book-off.jpeg"
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "total": "/Users/ayumu/my-projects/receipt-scanner-model/raw/book-off.jpeg"
    }
