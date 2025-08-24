from fastapi.testclient import TestClient
from pytest_mock import MockFixture
import pytest

from api.main import app, S3Client, handle_receipt_exception
from src.receipt_scanner_model.error import (
    S3BadRequest,
    S3NotFound,
    S3Forbidden,
    S3ServiceUnavailable,
    S3InternalServerError,
    S3UnexpectedError,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_root(client: TestClient):
    """
    APIのバージョンを確認するテスト
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"version": "0.1.0"}


def test_receipt_analyze_success(client: TestClient, mocker: MockFixture):
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


def test_receipt_analyze_with_extra_fields(client: TestClient, mocker: MockFixture):
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

    def test_missing_filename_field(self, client: TestClient):
        """filenameフィールドが欠落"""
        response = client.post("/receipt-analyze", json={})
        assert response.status_code == 422
        assert (
            response.json()["detail"]
            == "レシート解析中にエラーが起きました。再度レシートをアップロードしてください。"
        )

    @pytest.mark.parametrize("empty_filename", ["", "   "])
    def test_empty_filename(self, client: TestClient, empty_filename):
        """filenameが空文字列"""
        response = client.post("/receipt-analyze", json={"filename": empty_filename})
        assert response.status_code == 422
        assert (
            response.json()["detail"]
            == "レシート解析中にエラーが起きました。再度レシートをアップロードしてください。"
        )

    def test_null_filename(self, client: TestClient):
        """filenameがnull"""
        response = client.post("/receipt-analyze", json={"filename": None})
        assert response.status_code == 422
        assert (
            response.json()["detail"]
            == "レシート解析中にエラーが起きました。再度レシートをアップロードしてください。"
        )

    @pytest.mark.parametrize("invalid_filename", [123, [], {}, True, ["test.jpg"], 1.5])
    def test_invalid_filename_type(self, client: TestClient, invalid_filename):
        """filenameが文字列以外"""
        response = client.post("/receipt-analyze", json={"filename": invalid_filename})
        assert response.status_code == 422
        assert (
            response.json()["detail"]
            == "レシート解析中にエラーが起きました。再度レシートをアップロードしてください。"
        )

    def test_invalid_json_format(self, client: TestClient):
        """不正なJSONフォーマット"""
        response = client.post(
            "/receipt-analyze",
            content="{filename: test.jpg}",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422
        assert (
            response.json()["detail"]
            == "レシート解析中にエラーが起きました。再度レシートをアップロードしてください。"
        )

    def test_invalid_content_type(self, client: TestClient):
        """Content-Typeが不正"""
        response = client.post(
            "/receipt-analyze",
            json={"filename": "test.jpg"},
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 422
        assert (
            response.json()["detail"]
            == "レシート解析中にエラーが起きました。再度レシートをアップロードしてください。"
        )

    @pytest.mark.parametrize(
        "invalid_filename",
        [
            "../../../etc/passwd",  # パストラバーサル攻撃
            "file|rm -rf /",  # コマンドインジェクション
            "file\x00.jpg",  # ヌル文字インジェクション
            "CON",  # Windows予約語
            "aux.jpg",  # Windows予約語
            "file\n.jpg",  # 改行文字
        ],
    )
    def test_dangerous_filename_patterns(self, client: TestClient, invalid_filename):
        """危険なファイル名パターンのテスト"""
        response = client.post("/receipt-analyze", json={"filename": invalid_filename})
        assert response.status_code == 422
        assert (
            response.json()["detail"]
            == "レシート解析中にエラーが起きました。再度レシートをアップロードしてください。"
        )


class TestS3ErrorHandling:
    """
    S3関連のエラーに関するテスト
    """

    def test_s3_bad_request_exception(self, client: TestClient, mocker: MockFixture):
        """S3BadRequest例外"""
        mocker.patch.object(
            S3Client,
            "download_image_by_filename",
            side_effect=S3BadRequest(400, "Bad request"),
        )

        response = client.post("/receipt-analyze", json={"filename": "test.jpg"})

        assert response.status_code == 400
        assert (
            response.json()["detail"]
            == "レシート解析中にエラーが起きました。再度レシートをアップロードしてください。"
        )

    def test_s3_not_found_exception(self, client: TestClient, mocker: MockFixture):
        """S3NotFound例外"""
        mocker.patch.object(
            S3Client,
            "download_image_by_filename",
            side_effect=S3NotFound(404, "Not found"),
        )

        response = client.post("/receipt-analyze", json={"filename": "not_exists.jpg"})

        assert response.status_code == 400
        assert (
            response.json()["detail"]
            == "レシート解析中にエラーが起きました。再度レシートをアップロードしてください。"
        )

    def test_s3_service_unavailable_exception(
        self, client: TestClient, mocker: MockFixture
    ):
        """S3ServiceUnavailable例外"""
        mocker.patch.object(
            S3Client,
            "download_image_by_filename",
            side_effect=S3ServiceUnavailable(503, "Service unavailable"),
        )

        response = client.post("/receipt-analyze", json={"filename": "test.jpg"})

        assert response.status_code == 503
        assert (
            response.json()["detail"]
            == "レシート解析中にエラーが起きました。しばらくしてから再度お試しください。"
        )

    def test_s3_forbidden_exception(self, client: TestClient, mocker: MockFixture):
        """S3Forbidden例外（権限不足）"""
        mocker.patch.object(
            S3Client,
            "download_image_by_filename",
            side_effect=S3Forbidden(403, "Forbidden"),
        )

        response = client.post("/receipt-analyze", json={"filename": "test.jpg"})

        assert response.status_code == 500
        assert (
            response.json()["detail"]
            == "レシート解析中にエラーが起きました。サポートまでお問い合わせください"
        )

    def test_s3_internal_service_error_exception(
        self, client: TestClient, mocker: MockFixture
    ):
        """S3InternalServiceError例外"""
        mocker.patch.object(
            S3Client,
            "download_image_by_filename",
            side_effect=S3InternalServerError(500, "Internal error"),
        )

        response = client.post("/receipt-analyze", json={"filename": "test.jpg"})

        assert response.status_code == 500
        assert (
            response.json()["detail"]
            == "レシート解析中にエラーが起きました。しばらくしてから再度お試しください。"
        )

    def test_s3_unexpected_error_exception(
        self, client: TestClient, mocker: MockFixture
    ):
        """S3UnexpectedError例外"""
        mocker.patch.object(
            S3Client,
            "download_image_by_filename",
            side_effect=S3UnexpectedError(500, "Unexpected error"),
        )

        response = client.post("/receipt-analyze", json={"filename": "test.jpg"})

        assert response.status_code == 500
        assert (
            response.json()["detail"]
            == "レシート解析中にエラーが起きました。しばらくしてから再度お試しください。問題が継続する場合は、サポートまでお問い合わせください"
        )


class TestInternalServerErrors:
    """
    内部サーバーエラーと予期しない例外
    """

    def test_unexpected_exception(self, client: TestClient, mocker: MockFixture):
        """画像ダウンロード中の予期せぬ例外"""
        mocker.patch.object(
            S3Client,
            "download_image_by_filename",
            side_effect=ValueError("unexpected error"),
        )

        response = client.post("/receipt-analyze", json={"filename": "test.jpg"})

        assert response.status_code == 500
        assert (
            response.json()["detail"]
            == "レシート解析中にエラーが起きました。しばらくしてから再度お試しください。問題が継続する場合は、サポートまでお問い合わせください"
        )

    def test_s3_client_initialization_failure(
        self, client: TestClient, mocker: MockFixture
    ):
        """S3Client初期化失敗"""
        mocker.patch(
            "api.main.S3Client", side_effect=AttributeError("S3Client init failed")
        )

        response = client.post("/receipt-analyze", json={"filename": "test.jpg"})

        assert response.status_code == 500
        assert (
            response.json()["detail"]
            == "レシート解析中にエラーが起きました。しばらくしてから再度お試しください。問題が継続する場合は、サポートまでお問い合わせください"
        )

    def test_get_receipt_detail_failure(self, client: TestClient, mocker: MockFixture):
        # FIXME get_receipt_detailのエラーハンドリングを整備後に詳細なテストが必要。
        """get_receipt_detail関数でのエラー"""
        mocker.patch.object(
            S3Client, "download_image_by_filename", return_value=b"mock_image_bytes"
        )
        mocker.patch(
            "api.main.get_receipt_detail",
            side_effect=RuntimeError("Receipt analysis failed"),
        )

        response = client.post("/receipt-analyze", json={"filename": "test.jpg"})

        assert response.status_code == 500
        assert (
            response.json()["detail"]
            == "レシート解析中にエラーが起きました。しばらくしてから再度お試しください。問題が継続する場合は、サポートまでお問い合わせください"
        )


class TestHandleReceiptException:
    """
    handle_receipt_exception関数の単体テスト
    """

    def test_handle_s3_bad_request(self):
        """S3BadRequest例外の処理"""
        exception = S3BadRequest(400, "Bad request")
        result = handle_receipt_exception(exception, "test.jpg")

        assert result.status_code == 400
        assert (
            result.detail
            == "レシート解析中にエラーが起きました。再度レシートをアップロードしてください。"
        )

    def test_handle_s3_not_found(self):
        """S3NotFound例外の処理"""
        exception = S3NotFound(404, "Not found")
        result = handle_receipt_exception(exception, "test.jpg")

        assert result.status_code == 400
        assert (
            result.detail
            == "レシート解析中にエラーが起きました。再度レシートをアップロードしてください。"
        )

    def test_handle_s3_service_unavailable(self):
        """S3ServiceUnavailable例外の処理"""
        exception = S3ServiceUnavailable(503, "Service unavailable")
        result = handle_receipt_exception(exception, "test.jpg")

        assert result.status_code == 503
        assert (
            result.detail
            == "レシート解析中にエラーが起きました。しばらくしてから再度お試しください。"
        )

    def test_handle_s3_forbidden(self):
        """S3Forbidden例外の処理"""
        exception = S3Forbidden(403, "Forbidden")
        result = handle_receipt_exception(exception, "test.jpg")

        assert result.status_code == 500
        assert (
            result.detail
            == "レシート解析中にエラーが起きました。サポートまでお問い合わせください"
        )

    def test_handle_s3_internal_service_error(self):
        """S3InternalServiceError例外の処理"""
        exception = S3InternalServerError(500, "Internal error")
        result = handle_receipt_exception(exception, "test.jpg")

        assert result.status_code == 500
        assert (
            result.detail
            == "レシート解析中にエラーが起きました。しばらくしてから再度お試しください。"
        )

    def test_handle_s3_unexpected_error(self):
        """S3UnexpectedError例外の処理"""
        exception = S3UnexpectedError(500, "Unexpected error")
        result = handle_receipt_exception(exception, "test.jpg")

        assert result.status_code == 500
        assert (
            result.detail
            == "レシート解析中にエラーが起きました。しばらくしてから再度お試しください。問題が継続する場合は、サポートまでお問い合わせください"
        )

    def test_handle_unknown_exception(self):
        """予期せぬ例外の処理"""
        exception = ValueError("Unknown error")
        result = handle_receipt_exception(exception, "test.jpg")

        assert result.status_code == 500
        assert (
            result.detail
            == "レシート解析中にエラーが起きました。しばらくしてから再度お試しください。問題が継続する場合は、サポートまでお問い合わせください"
        )

    def test_handle_exception_with_none_filename(self):
        """filename引数がNoneの場合"""
        exception = ValueError("Unknown error")
        result = handle_receipt_exception(exception, None)

        assert result.status_code == 500
        assert (
            result.detail
            == "レシート解析中にエラーが起きました。しばらくしてから再度お試しください。問題が継続する場合は、サポートまでお問い合わせください"
        )
