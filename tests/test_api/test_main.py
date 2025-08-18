from fastapi.testclient import TestClient
from pytest_mock import MockFixture

from api.main import app, S3Client

client = TestClient(app)


def test_root():
    """
    APIのバージョンを確認するテスト
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"version": "0.1.0"}


def test_receipt_analyze_success(mocker: MockFixture):
    """
    レシート解析が成功する場合のテスト
    """
    # S3Clientのdownload_image_by_filenameメソッドをモック
    mock_s3_client = mocker.patch.object(
        S3Client, "download_image_by_filename", return_value=b"mock_image_bytes"
    )

    # get_receipt_detail関数をモック
    mock_get_receipt_detail = mocker.patch(
        "api.main.get_receipt_detail",
        return_value={
            "store_name": "テストストア",
            "amount": 1000,
            "date": "2024/01/01",
            "category": "食費",
        },
    )

    # APIリクエスト
    response = client.post("/receipt-analyze", json={"filename": "test.jpg"})

    # レスポンスの検証
    assert response.status_code == 200
    assert response.json() == {
        "store_name": "テストストア",
        "amount": 1000,
        "date": "2024/01/01",
        "category": "食費",
    }

    # モック関数が正しく呼び出されたことを確認
    mock_s3_client.assert_called_once_with("test.jpg")
    mock_get_receipt_detail.assert_called_once_with(b"mock_image_bytes")
