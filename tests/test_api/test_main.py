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
    """正常なレシート解析処理"""
    mock_s3_client = mocker.patch.object(
        S3Client, "download_image_by_filename", return_value=b"mock_image_bytes"
    )

    mock_get_receipt_detail = mocker.patch(
        "api.main.get_receipt_detail",
        return_value={
            "store_name": "テストストア",
            "amount": 1000,
            "date": "2024/01/01",
            "category": "食費",
        },
    )

    response = client.post("/receipt-analyze", json={"filename": "test.jpg"})

    assert response.status_code == 200
    assert response.json() == {
        "store_name": "テストストア",
        "amount": 1000,
        "date": "2024/01/01",
        "category": "食費",
    }

    mock_s3_client.assert_called_once_with("test.jpg")
    mock_get_receipt_detail.assert_called_once_with(b"mock_image_bytes")


def test_receipt_analyze_with_extra_fields(mocker: MockFixture):
    # NOTE: 現在は正常系としているが、422にする可能性あり。
    """余分なフィールドがあっても正常処理されること"""
    mock_s3_client = mocker.patch.object(
        S3Client, "download_image_by_filename", return_value=b"mock_image_bytes"
    )
    mocker.patch(
        "api.main.get_receipt_detail",
        return_value={
            "store_name": "Store",
            "amount": 100,
            "date": "2024/01/01",
            "category": "食費",
        },
    )

    response = client.post(
        "/receipt-analyze",
        json={"filename": "test.jpg", "extra_field": "ignored", "another_field": 123},
    )

    assert response.status_code == 200
    mock_s3_client.assert_called_once_with("test.jpg")
