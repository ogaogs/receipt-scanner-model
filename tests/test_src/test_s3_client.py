from pytest_mock import MockFixture
import pytest
import io
from botocore.exceptions import (
    ClientError,
    EndpointConnectionError,
    ConnectTimeoutError,
)
from src.receipt_scanner_model.s3_client import S3Client, MAX_FILE_SIZE
from src.receipt_scanner_model.error import (
    S3BadRequest,
    S3NotFound,
    S3Forbidden,
    S3ServiceUnavailable,
    S3InternalServerError,
    S3UnexpectedError,
)


@pytest.fixture
def s3_client():
    return S3Client()


@pytest.fixture
def mock_boto3_client(mocker: MockFixture):
    """boto3.client関数自体をモック（初期化パラメータのテスト用）"""
    return mocker.patch("src.receipt_scanner_model.s3_client.boto3.client")


@pytest.fixture
def mock_aws_s3_client(mocker: MockFixture):
    """S3クライアントインスタンスをモック（S3操作のテスト用）"""
    return mocker.patch("src.receipt_scanner_model.s3_client.boto3.client").return_value


def setup_s3_mocks(
    mock_s3_client,
    content_length=1024,
    file_content=b"test_content",
    content_type="image/png",
):
    """S3モックの共通セットアップ"""
    mock_s3_client.head_object.return_value = {
        "ContentLength": content_length,
        "ContentType": content_type,
    }
    mock_s3_client.get_object.return_value = {"Body": io.BytesIO(file_content)}


def test_init_creates_s3_client_with_specific_parameters(mocker, mock_boto3_client):
    """初期化時にS3クライアントが特定のパラメータで正しく作成されることをテスト"""
    # 特定の値でモック設定を行い、正しく反映されるかを確認
    mock_setting = mocker.patch("src.receipt_scanner_model.s3_client.setting")
    mock_setting.bucket_name = "test-bucket"
    mock_setting.aws_default_region = "ap-northeast-1"
    mock_setting.aws_access_key_id = "test-key-id"
    mock_setting.aws_secret_access_key = "test-secret"

    client = S3Client()

    # 特定の値が正しくboto3.clientに渡されることを確認
    mock_boto3_client.assert_called_once_with(
        "s3",
        region_name="ap-northeast-1",
        aws_access_key_id="test-key-id",
        aws_secret_access_key="test-secret",
    )
    assert client.bucket_name == "test-bucket"


def test_download_image_by_filename_success(mock_aws_s3_client, s3_client):
    """download_image_by_filenameが正常に動作することをテスト"""
    test_filename = "test_receipt.jpg"
    file_content = b"test_image_content"
    content_type = "image/png"

    setup_s3_mocks(mock_aws_s3_client, content_length=1024, file_content=file_content)

    file_content_result, content_type_result = s3_client.download_image_by_filename(
        test_filename
    )

    # head_objectとget_objectが正しいパラメータで呼ばれたことを確認
    mock_aws_s3_client.head_object.assert_called_once_with(
        Bucket=s3_client.bucket_name, Key=test_filename
    )
    mock_aws_s3_client.get_object.assert_called_once_with(
        Bucket=s3_client.bucket_name, Key=test_filename
    )

    # 戻り値が期待通りであることを確認
    assert file_content_result == file_content
    assert content_type_result == content_type


@pytest.mark.parametrize(
    "file_size,expected_success,expected_message",
    [
        # 下限境界値テスト
        (-1, False, "ファイルサイズが0バイト以下です"),
        (0, False, "ファイルサイズが0バイト以下です"),
        (1, True, None),
        # 上限境界値テスト (5MB = 5,242,880 bytes)
        (MAX_FILE_SIZE - 1, True, None),  # 最大値-1
        (MAX_FILE_SIZE, True, None),  # 最大値
        (MAX_FILE_SIZE + 1, False, "ファイルサイズが制限を超えています"),  # 最大値+1
    ],
)
def test_file_size_boundary_values(
    mock_aws_s3_client, s3_client, file_size, expected_success, expected_message
):
    """境界値テスト: ファイルサイズの上限・下限値"""
    test_filename = "test_receipt.jpg"
    file_content = b"test_content"
    content_type = "image/png"

    if expected_success:
        # 正常ケース
        setup_s3_mocks(
            mock_aws_s3_client,
            content_length=file_size,
            file_content=file_content,
            content_type=content_type,
        )
        file_content_result, content_type_result = s3_client.download_image_by_filename(
            test_filename
        )
        assert file_content_result == file_content
        assert content_type_result == content_type
    else:
        # エラーケース: head_objectのみセットアップ
        mock_aws_s3_client.head_object.return_value = {
            "ContentLength": file_size,
            "ContentType": content_type,
        }
        with pytest.raises(S3BadRequest) as exc_info:
            s3_client.download_image_by_filename(test_filename)
        assert exc_info.value.code == 400
        assert expected_message in exc_info.value.message


@pytest.mark.parametrize(
    "status_code,error_message,expected_exception,expected_message",
    [
        (400, "Bad Request", S3BadRequest, "不正なリクエストです: Bad Request"),
        (403, "Forbidden", S3Forbidden, "アクセスが拒否されました: Forbidden"),
        (404, "Not Found", S3NotFound, "指定されたファイルがS3にありません: Not Found"),
        (
            500,
            "Internal Server Error",
            S3InternalServerError,
            "S3サービスでInternalServerErrorが発生しました: Internal Server Error",
        ),
        (
            503,
            "Service Unavailable",
            S3ServiceUnavailable,
            "S3サービスが一時的に利用できません: Service Unavailable",
        ),
    ],
)
def test_download_image_by_filename_client_errors(
    mock_aws_s3_client,
    s3_client,
    status_code,
    error_message,
    expected_exception,
    expected_message,
):
    """download_fileobjの実行中にClientErrorが発生した際のテスト"""
    test_file = "test_file.jpg"

    setup_s3_mocks(mock_aws_s3_client)

    mock_aws_s3_client.get_object.side_effect = ClientError(
        {
            "Error": {"Message": error_message},
            "ResponseMetadata": {"HTTPStatusCode": status_code},
        },
        "DownloadFileObj",
    )

    with pytest.raises(expected_exception) as exc_info:
        s3_client.download_image_by_filename(test_file)

    assert exc_info.value.code == status_code
    assert exc_info.value.message == expected_message


@pytest.mark.parametrize(
    "status_code,error_message",
    [
        (405, "Method Not Allowed"),
        (409, "Conflict"),
        (411, "Length Required"),
        (412, "Precondition Failed"),
    ],
)
def test_download_image_by_filename_unexpected_client_error(
    mock_aws_s3_client, s3_client, status_code, error_message
):
    """download_fileobjの実行中に予期せぬS3clientエラーが発生した際のテスト"""
    unexpected_client_error_file = "unexpected_client_error_file.jpg"

    setup_s3_mocks(mock_aws_s3_client)

    mock_aws_s3_client.get_object.side_effect = ClientError(
        {
            "Error": {"Message": error_message},
            "ResponseMetadata": {"HTTPStatusCode": status_code},
        },
        "DownloadFileObj",
    )

    with pytest.raises(S3UnexpectedError) as exc_info:
        s3_client.download_image_by_filename(unexpected_client_error_file)

    assert exc_info.value.code == status_code
    assert (
        exc_info.value.message
        == f"ダウンロード中に予期しないエラーが発生しました: {error_message}"
    )


def test_download_image_by_filename_unexpected_error(mock_aws_s3_client, s3_client):
    """予期していないエラー：Body.read()でIOErrorが発生した際のテスト"""
    unexpected_error_file = "unexpected_error_file.jpg"

    # head_objectの正常レスポンス
    mock_aws_s3_client.head_object.return_value = {
        "ContentLength": 1024,
        "ContentType": "image/png",
    }

    # get_objectでモックのBodyオブジェクトを作成
    from unittest.mock import Mock

    mock_body = Mock()
    mock_body.read.side_effect = IOError("データ読み取りエラー")
    mock_aws_s3_client.get_object.return_value = {"Body": mock_body}

    with pytest.raises(S3UnexpectedError) as exc_info:
        s3_client.download_image_by_filename(unexpected_error_file)

    assert exc_info.value.code == 500
    assert "ダウンロード中に予期しないエラーが発生しました" in exc_info.value.message


def test_head_object_error(mock_aws_s3_client, s3_client):
    """head_object自体がエラーになるケース（get_objectに到達しない）"""
    test_filename = "test.jpg"

    # head_objectで直接404エラー（ファイルが存在しない）
    mock_aws_s3_client.head_object.side_effect = ClientError(
        {
            "Error": {"Message": "Not Found"},
            "ResponseMetadata": {"HTTPStatusCode": 404},
        },
        "HeadObject",
    )

    with pytest.raises(S3NotFound):
        s3_client.download_image_by_filename(test_filename)

    # get_objectは呼ばれないことを確認
    mock_aws_s3_client.get_object.assert_not_called()


@pytest.mark.parametrize(
    "exception_type,error_message",
    [
        (
            EndpointConnectionError(endpoint_url="https://s3.amazonaws.com"),
            "エンドポイント接続エラー",
        ),
        (
            ConnectTimeoutError(endpoint_url="https://s3.amazonaws.com", timeout=30),
            "接続タイムアウト",
        ),
    ],
)
def test_unexpected_error(mock_aws_s3_client, s3_client, exception_type, error_message):
    """ClientError以外の予期しないエラーをテスト"""
    test_filename = "network_error_test.jpg"

    # head_objectでネットワークエラーが発生
    mock_aws_s3_client.head_object.side_effect = exception_type

    with pytest.raises(S3UnexpectedError) as exc_info:
        s3_client.download_image_by_filename(test_filename)

    assert exc_info.value.code == 500
    assert "ダウンロード中に予期しないエラーが発生しました" in exc_info.value.message


@pytest.mark.parametrize(
    "file_name, content_type",
    [
        ("test_file.pdf", "application/pdf"),
        ("test_file.gif", "image/gif"),
    ],
)
def test_invalid_content_type(file_name, content_type, mock_aws_s3_client, s3_client):
    """Content-Typeが画像でない場合のテスト（lines 68-74のカバレッジ）"""

    mock_aws_s3_client.head_object.return_value = {
        "ContentLength": 1024,
        "ContentType": content_type,
    }

    with pytest.raises(S3BadRequest) as exc_info:
        s3_client.download_image_by_filename(file_name)

    assert exc_info.value.code == 400
