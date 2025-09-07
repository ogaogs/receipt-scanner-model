from pytest_mock import MockFixture
import pytest
from src.receipt_scanner_model.open_ai import ReceiptDetail
from src.receipt_scanner_model.error import (
    OpenAIAuthenticationError,
    OpenAIServiceUnavailable,
    OpenAIUnexpectedError,
    OpenAIResponseFormatError,
)
from src.receipt_scanner_model.analyze import get_receipt_detail

TEST_IMAGE_BYTES = b"MockImageBytesForTesting"
TEST_IMAGE_TYPE = "png"
TEST_BASE64_IMAGE = "data:image/png;base64,MockImageDataForTesting"


@pytest.fixture
def test_receipt_detail() -> ReceiptDetail:
    return ReceiptDetail(
        store_name="Test Store",
        date="2023/10/01",
        amount=1500,
        category="食費",
    )


@pytest.fixture
def mock_encode_image(mocker: MockFixture):
    return mocker.patch(
        "src.receipt_scanner_model.analyze.encode_image",
        return_value=TEST_BASE64_IMAGE,
    )


@pytest.fixture
def mock_openai_handler(mocker: MockFixture):
    return mocker.patch("src.receipt_scanner_model.analyze.OpenAIHandler").return_value


def test_get_receipt_detail_success(
    mock_openai_handler,
    test_receipt_detail: ReceiptDetail,
):
    mock_openai_handler.analyze_image.return_value = test_receipt_detail

    result = get_receipt_detail(TEST_IMAGE_BYTES, TEST_IMAGE_TYPE)

    assert result.store_name == test_receipt_detail.store_name
    assert result.date == test_receipt_detail.date
    assert result.amount == test_receipt_detail.amount
    assert result.category == test_receipt_detail.category


@pytest.mark.parametrize(
    "exception",
    [
        OpenAIAuthenticationError,
        OpenAIServiceUnavailable,
        OpenAIUnexpectedError,
        OpenAIResponseFormatError,
    ],
)
def test_get_receipt_detail_error_handling(
    mock_openai_handler,
    exception,
):
    mock_openai_handler.analyze_image.side_effect = exception

    with pytest.raises(exception) as exc_info:
        get_receipt_detail(TEST_IMAGE_BYTES, TEST_IMAGE_TYPE)

    assert exc_info.type == exception
