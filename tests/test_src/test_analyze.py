from pytest_mock import MockFixture
import pytest
from src.receipt_scanner_model.open_ai import OpenAIHandler, ReceiptDetail
from src.receipt_scanner_model.error import (
    OpenAIAuthenticationError,
    OpenAIServiceUnavailable,
    OpenAIUnexpectedError,
    OpenAIResponseFormatError,
)
from src.receipt_scanner_model.analyze import get_receipt_detail


@pytest.fixture
def mock_encode_image(
    mocker: MockFixture,
):
    return mocker.patch(
        "src.receipt_scanner_model.file_operations.encode_image",
        return_value="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD...",
    )


@pytest.fixture
def mock_analyze_image(mocker: MockFixture):
    mock_response = ReceiptDetail(
        store_name="Test Store", date="2023/10/01", amount=1500, category="食費"
    )
    return mocker.patch.object(
        OpenAIHandler, "analyze_image", return_value=mock_response
    )


def test_analyze_image_success(
    mocker: MockFixture, mock_encode_image, mock_analyze_image
):
    """get_receipt_detailが正常に動作することをテスト"""
    test_image_bytes = b"test_image_bytes"

    result = get_receipt_detail(test_image_bytes)
    assert result.store_name == "Test Store"
    assert result.date == "2023/10/01"
    assert result.amount == 1500
    assert result.category == "食費"


@pytest.mark.parametrize(
    "exception, status_code, expected_message",
    [
        (
            OpenAIAuthenticationError,
            401,
            "OpenAIの認証に失敗しました。APIキーを確認してください。",
        ),
        (
            OpenAIServiceUnavailable,
            503,
            "OpenAIのサービスが一時的に利用できません。時間をおいて再度お試しください。",
        ),
        (
            OpenAIUnexpectedError,
            500,
            "OpenAIの予期しないエラーが発生しました。",
        ),
        (
            OpenAIResponseFormatError,
            503,
            "OpenAIの応答の解析に失敗しました。",
        ),
    ],
)
def test_authentication_error(
    mocker: MockFixture,
    mock_encode_image,
    exception,
    status_code,
    expected_message,
):
    """AuthenticationErrorがOpenAIAuthenticationErrorに変換されることをテスト"""
    test_image_bytes = b"test_image_bytes"

    mocker.patch.object(
        OpenAIHandler,
        "analyze_image",
        side_effect=exception(status_code, expected_message),
    )

    with pytest.raises(exception) as exc_info:
        get_receipt_detail(test_image_bytes)
    assert exc_info.value.code == status_code
    assert exc_info.value.message == expected_message
