from fastapi.testclient import TestClient
from pytest_mock import MockFixture
import pytest

from api.main import app, S3Client, handle_receipt_exception
from src.receipt_scanner_model.error import (
    ContentSizeError,
    InvalidContentTypeError,
    S3BadRequest,
    S3NotFound,
    S3Forbidden,
    S3ServiceUnavailable,
    S3InternalServerError,
    S3UnexpectedError,
    ErrorCode,
    OpenAIResponseFormatError,
    OpenAIServiceUnavailable,
    OpenAIAuthenticationError,
    OpenAIUnexpectedError,
)
import tomllib

TEST_FILE_NAME = "test.png"
MOCK_IMAGE_BYTES = b"mock_image_bytes"


@pytest.fixture
def client():
    return TestClient(app)


def test_root(client: TestClient):
    """
    APIのバージョンを確認するテスト
    """
    response = client.get("/")

    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    version = data["project"]["version"]

    assert response.status_code == 200
    assert response.json() == {"version": version}


def test_receipt_analyze_success(client: TestClient, mocker: MockFixture):
    """正常なレシート解析処理"""
    test_file_type = "png"
    mock_s3_client = mocker.patch.object(
        S3Client,
        "download_image_by_filename",
        return_value=(MOCK_IMAGE_BYTES, test_file_type),
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

    response = client.post("/receipt-analyze", json={"filename": TEST_FILE_NAME})

    assert response.status_code == 200
    assert response.json() == {
        "store_name": "テストストア",
        "amount": 1000,
        "date": "2024/01/01",
        "category": "食費",
    }

    mock_s3_client.assert_called_once_with(TEST_FILE_NAME)
    mock_get_receipt_detail.assert_called_once_with(MOCK_IMAGE_BYTES, test_file_type)


def test_receipt_analyze_with_extra_fields(client: TestClient, mocker: MockFixture):
    # NOTE: 現在は正常系としているが、422にする可能性あり。
    """余分なフィールドがあっても正常処理されること"""

    test_file_type = "png"

    mock_s3_client = mocker.patch.object(
        S3Client,
        "download_image_by_filename",
        return_value=(MOCK_IMAGE_BYTES, test_file_type),
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
        json={
            "filename": TEST_FILE_NAME,
            "extra_field": "ignored",
            "another_field": 123,
        },
    )

    assert response.status_code == 200
    mock_s3_client.assert_called_once_with(TEST_FILE_NAME)


class TestInputValidation:
    """
    リクエスト形式に関するテスト
    """

    # 400 Bad Request
    def test_missing_filename_field(self, client: TestClient):
        """filenameフィールドが欠落"""
        response = client.post("/receipt-analyze", json={})
        assert response.status_code == 400
        assert response.json() == {
            "error_type_code": ErrorCode.CLIENT_ERROR.value,
            "message": "リクエストが不正です。",
        }

    def test_invalid_json_format(self, client: TestClient):
        """不正なJSONフォーマット"""
        response = client.post(
            "/receipt-analyze",
            content="{filename: test.png}",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        assert response.json() == {
            "error_type_code": ErrorCode.CLIENT_ERROR.value,
            "message": "リクエストが不正です。",
        }

    # 415 Unsupported Media Type
    def test_invalid_content_type(self, client: TestClient):
        """Content-Typeが不正"""
        response = client.post(
            "/receipt-analyze",
            json={"filename": TEST_FILE_NAME},
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 415
        assert response.json() == {
            "error_type_code": ErrorCode.CLIENT_ERROR.value,
            "message": "リクエストのContent-Typeが不正です。",
        }

    # 422 Unprocessable Entity
    @pytest.mark.parametrize("empty_filename", ["", "   "])
    def test_empty_filename(self, client: TestClient, empty_filename):
        """filenameが空文字列"""
        response = client.post("/receipt-analyze", json={"filename": empty_filename})
        assert response.status_code == 422
        assert response.json() == {
            "error_type_code": ErrorCode.CLIENT_ERROR.value,
            "message": "リクエストのバリデーションに失敗しました。入力内容を確認してください。",
        }

    def test_null_filename(self, client: TestClient):
        """filenameがnull"""
        response = client.post("/receipt-analyze", json={"filename": None})
        assert response.status_code == 422
        assert response.json() == {
            "error_type_code": ErrorCode.CLIENT_ERROR.value,
            "message": "リクエストのバリデーションに失敗しました。入力内容を確認してください。",
        }

    @pytest.mark.parametrize(
        "invalid_filename", [123, [], {}, True, [TEST_FILE_NAME], 1.5]
    )
    def test_invalid_filename_type(self, client: TestClient, invalid_filename):
        """filenameが文字列以外"""
        response = client.post("/receipt-analyze", json={"filename": invalid_filename})
        assert response.status_code == 422
        assert response.json() == {
            "error_type_code": ErrorCode.CLIENT_ERROR.value,
            "message": "リクエストのバリデーションに失敗しました。入力内容を確認してください。",
        }

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
        assert response.json() == {
            "error_type_code": ErrorCode.CLIENT_ERROR.value,
            "message": "リクエストのバリデーションに失敗しました。入力内容を確認してください。",
        }


class TestS3ErrorHandling:
    """
    S3関連のエラーに関するテスト
    """

    def test_s3_bad_request_exception(self, client: TestClient, mocker: MockFixture):
        """S3BadRequest例外"""
        mocker.patch.object(
            S3Client,
            "download_image_by_filename",
            side_effect=S3BadRequest,
        )

        response = client.post("/receipt-analyze", json={"filename": TEST_FILE_NAME})

        assert response.status_code == 500
        assert response.json() == {
            "error_type_code": ErrorCode.SERVER_ERROR.value,
            "message": "レシート解析中にエラーが起きました。しばらくしてから再度お試しください。問題が継続する場合は、サポートまでお問い合わせください",
        }

    def test_s3_not_found_exception(self, client: TestClient, mocker: MockFixture):
        """S3NotFound例外"""
        filename = "not_exists.jpg"
        mocker.patch.object(
            S3Client,
            "download_image_by_filename",
            side_effect=S3NotFound,
        )

        response = client.post("/receipt-analyze", json={"filename": filename})

        assert response.status_code == 404
        assert response.json() == {
            "error_type_code": ErrorCode.CLIENT_ERROR.value,
            "message": f"指定されたファイル名({filename})が見つかりません。ファイルアップロードに問題がある可能性があります。",
        }

    def test_s3_service_unavailable_exception(
        self, client: TestClient, mocker: MockFixture
    ):
        """S3ServiceUnavailable例外"""
        mocker.patch.object(
            S3Client,
            "download_image_by_filename",
            side_effect=S3ServiceUnavailable,
        )

        response = client.post("/receipt-analyze", json={"filename": TEST_FILE_NAME})

        assert response.status_code == 503
        assert response.json() == {
            "error_type_code": ErrorCode.SERVER_ERROR.value,
            "message": "S3またはOpenAIのサービスが一時的に利用できません。時間をおいて再度お試しください。",
        }

    def test_s3_forbidden_exception(self, client: TestClient, mocker: MockFixture):
        """S3Forbidden例外（権限不足）"""
        mocker.patch.object(
            S3Client,
            "download_image_by_filename",
            side_effect=S3Forbidden,
        )

        response = client.post("/receipt-analyze", json={"filename": TEST_FILE_NAME})

        assert response.status_code == 500
        assert response.json() == {
            "error_type_code": ErrorCode.SERVER_ERROR.value,
            "message": "レシート解析中に権限エラーが起きました。",
        }

    def test_s3_internal_service_error_exception(
        self, client: TestClient, mocker: MockFixture
    ):
        """S3InternalServiceError例外"""
        mocker.patch.object(
            S3Client,
            "download_image_by_filename",
            side_effect=S3InternalServerError,
        )

        response = client.post("/receipt-analyze", json={"filename": TEST_FILE_NAME})

        assert response.status_code == 503
        assert response.json() == {
            "error_type_code": ErrorCode.SERVER_ERROR.value,
            "message": "S3またはOpenAIのサービスが一時的に利用できません。時間をおいて再度お試しください。",
        }

    def test_s3_unexpected_error_exception(
        self, client: TestClient, mocker: MockFixture
    ):
        """S3UnexpectedError例外"""
        mocker.patch.object(
            S3Client,
            "download_image_by_filename",
            side_effect=S3UnexpectedError,
        )

        response = client.post("/receipt-analyze", json={"filename": TEST_FILE_NAME})

        assert response.status_code == 500
        assert response.json() == {
            "error_type_code": ErrorCode.SERVER_ERROR.value,
            "message": "レシート解析中にエラーが起きました。しばらくしてから再度お試しください。問題が継続する場合は、サポートまでお問い合わせください",
        }


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

        response = client.post("/receipt-analyze", json={"filename": TEST_FILE_NAME})

        assert response.status_code == 500
        assert response.json() == {
            "error_type_code": ErrorCode.SERVER_ERROR.value,
            "message": "レシート解析中にエラーが起きました。しばらくしてから再度お試しください。問題が継続する場合は、サポートまでお問い合わせください",
        }

    def test_s3_client_initialization_failure(
        self, client: TestClient, mocker: MockFixture
    ):
        """S3Client初期化失敗"""
        mocker.patch(
            "api.main.S3Client", side_effect=AttributeError("S3Client init failed")
        )

        response = client.post("/receipt-analyze", json={"filename": TEST_FILE_NAME})

        assert response.status_code == 500
        assert response.json() == {
            "error_type_code": ErrorCode.SERVER_ERROR.value,
            "message": "レシート解析中にエラーが起きました。しばらくしてから再度お試しください。問題が継続する場合は、サポートまでお問い合わせください",
        }

    def test_get_receipt_detail_failure(self, client: TestClient, mocker: MockFixture):
        """get_receipt_detail関数でのエラー"""
        mocker.patch.object(
            S3Client, "download_image_by_filename", return_value=MOCK_IMAGE_BYTES
        )
        mocker.patch(
            "api.main.get_receipt_detail",
            side_effect=RuntimeError("Receipt analysis failed"),
        )

        response = client.post("/receipt-analyze", json={"filename": TEST_FILE_NAME})

        assert response.status_code == 500
        assert response.json() == {
            "error_type_code": ErrorCode.SERVER_ERROR.value,
            "message": "レシート解析中にエラーが起きました。しばらくしてから再度お試しください。問題が継続する場合は、サポートまでお問い合わせください",
        }


class TestHandleReceiptException:
    """
    handle_receipt_exception関数の単体テスト
    """

    def test_handle_content_size_error(self):
        """ContentSizeError例外の処理"""
        exception = ContentSizeError()
        result = handle_receipt_exception(exception, TEST_FILE_NAME)

        assert result.http_status_code == 400
        assert result.error_type_code == ErrorCode.SIZE_ERROR
        assert (
            result.message
            == f"ダウンロードした画像サイズが0バイト以下か、5242880より大きいです。ファイル名: {TEST_FILE_NAME}"
        )

    def test_handle_invalid_content_type_error(self):
        """InvalidContentTypeError例外の処理"""
        exception = InvalidContentTypeError()
        result = handle_receipt_exception(exception, TEST_FILE_NAME)

        assert result.http_status_code == 400
        assert result.error_type_code == ErrorCode.INVALID_TYPE
        assert (
            result.message
            == f"ダウンロードした画像のContent-Typeが不正です。ファイル名: {TEST_FILE_NAME}"
        )

    def test_handle_s3_not_found(self):
        """S3NotFound例外の処理"""
        exception = S3NotFound()
        result = handle_receipt_exception(exception, TEST_FILE_NAME)

        assert result.http_status_code == 404
        assert result.error_type_code == ErrorCode.CLIENT_ERROR
        assert (
            result.message
            == f"指定されたファイル名({TEST_FILE_NAME})が見つかりません。ファイルアップロードに問題がある可能性があります。"
        )

    def test_handle_openai_response_format_error(self):
        """OpenAIResponseFormatError例外の処理"""
        exception = OpenAIResponseFormatError()
        result = handle_receipt_exception(exception, TEST_FILE_NAME)

        assert result.http_status_code == 503
        assert result.error_type_code == ErrorCode.SERVER_ERROR
        assert (
            result.message
            == "解析結果が予期せぬ形式でした。再度解析をすることで、正常に動作する場合があります。問題が継続する場合は、サポートまでお問い合わせください。"
        )

    @pytest.mark.parametrize(
        "exception",
        [S3ServiceUnavailable(), S3InternalServerError(), OpenAIServiceUnavailable()],
    )
    def test_handle_service_unavailable(self, exception):
        """ServiceUnavailable例外の処理"""
        result = handle_receipt_exception(exception, TEST_FILE_NAME)

        assert result.http_status_code == 503
        assert result.error_type_code == ErrorCode.SERVER_ERROR
        assert (
            result.message
            == "S3またはOpenAIのサービスが一時的に利用できません。時間をおいて再度お試しください。"
        )

    def test_handle_s3_bad_request(self):
        """S3BadRequest例外の処理"""
        exception = S3BadRequest()
        result = handle_receipt_exception(exception, TEST_FILE_NAME)

        assert result.http_status_code == 500
        assert result.error_type_code == ErrorCode.SERVER_ERROR
        assert (
            result.message
            == "レシート解析中にエラーが起きました。しばらくしてから再度お試しください。問題が継続する場合は、サポートまでお問い合わせください"
        )

    @pytest.mark.parametrize("exception", [S3Forbidden(), OpenAIAuthenticationError()])
    def test_handle_authentication_exception(self, exception):
        """S3Forbidden例外の処理"""
        result = handle_receipt_exception(exception, TEST_FILE_NAME)

        assert result.http_status_code == 500
        assert result.error_type_code == ErrorCode.SERVER_ERROR
        assert result.message == "レシート解析中に権限エラーが起きました。"

    @pytest.mark.parametrize(
        "exception", [S3UnexpectedError(), OpenAIUnexpectedError(), ValueError()]
    )
    def test_handle_500_exception(self, exception):
        """予期せぬ例外の処理"""
        result = handle_receipt_exception(exception, TEST_FILE_NAME)

        assert result.http_status_code == 500
        assert result.error_type_code == ErrorCode.SERVER_ERROR
        assert (
            result.message
            == "レシート解析中にエラーが起きました。しばらくしてから再度お試しください。問題が継続する場合は、サポートまでお問い合わせください"
        )

    def test_handle_exception_with_none_filename(self):
        """filename引数がNoneの場合"""
        exception = ValueError()
        result = handle_receipt_exception(exception, None)

        assert result.http_status_code == 500
        assert result.error_type_code == ErrorCode.SERVER_ERROR
        assert (
            result.message
            == "レシート解析中にエラーが起きました。しばらくしてから再度お試しください。問題が継続する場合は、サポートまでお問い合わせください"
        )
