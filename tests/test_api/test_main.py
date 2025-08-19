from fastapi.testclient import TestClient
from pytest_mock import MockFixture
import pytest

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


class TestInputValidation:
    """
    リクエスト形式に関するテスト
    """

    def test_missing_filename_field(self):
        """filenameフィールドが欠落"""
        response = client.post("/receipt-analyze", json={})
        assert response.status_code == 422

    def test_empty_filename(self):
        """filenameが空文字列"""
        response = client.post("/receipt-analyze", json={"filename": ""})
        assert response.status_code == 422

    def test_null_filename(self):
        """filenameがnull"""
        response = client.post("/receipt-analyze", json={"filename": None})
        assert response.status_code == 422

    @pytest.mark.parametrize("invalid_filename", [123, [], {}, True, ["test.jpg"]])
    def test_invalid_filename_type(self, invalid_filename):
        """filenameが文字列以外"""
        response = client.post("/receipt-analyze", json={"filename": invalid_filename})
        assert response.status_code == 422

    def test_invalid_json_format(self):
        """不正なJSONフォーマット"""
        response = client.post(
            "/receipt-analyze",
            data="{filename: test.jpg}",  # type: ignore
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_invalid_content_type(self):
        """Content-Typeが不正"""
        response = client.post(
            "/receipt-analyze",
            json={"filename": "test.jpg"},
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 422
