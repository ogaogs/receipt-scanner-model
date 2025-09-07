from pytest_mock import MockFixture
import pytest
from src.receipt_scanner_model.open_ai import OpenAIHandler, ReceiptDetail
from src.receipt_scanner_model.error import (
    OpenAIAuthenticationError,
    OpenAIServiceUnavailable,
    OpenAIUnexpectedError,
    OpenAIResponseFormatError,
)
from openai.types.chat.parsed_chat_completion import (
    ParsedChatCompletion,
    ParsedChoice,
    ParsedChatCompletionMessage,
)
from openai import (
    APITimeoutError,
    PermissionDeniedError,
    InternalServerError,
    RateLimitError,
    AuthenticationError,
)

TEST_BASE64_IMAGE = "data:image/png;base64,MockImageDataForTesting"
TEST_IMAGE_TYPE = "png"


def create_mock_completion(parsed_data=None):
    return ParsedChatCompletion[ReceiptDetail](
        id="chatcmpl-Test1234567890",
        choices=[
            ParsedChoice[ReceiptDetail](
                finish_reason="stop",
                index=0,
                logprobs=None,
                message=ParsedChatCompletionMessage[ReceiptDetail](
                    content=str(parsed_data) if parsed_data else None,
                    refusal=None,
                    role="assistant",
                    annotations=[],
                    audio=None,
                    function_call=None,
                    tool_calls=None,
                    parsed=parsed_data,
                ),
            )
        ],
        created=1756420606,
        model=OpenAIHandler.MODEL,
        object="chat.completion",
    )


@pytest.fixture
def test_receipt_detail() -> ReceiptDetail:
    return ReceiptDetail(
        store_name="Test Store",
        date="2023/10/01",
        amount=1500,
        category="食費",
    )


@pytest.fixture
def mock_openai_client(mocker: MockFixture):
    mock_client = mocker.MagicMock()
    mocker.patch("src.receipt_scanner_model.open_ai.OpenAI", return_value=mock_client)
    return mock_client


@pytest.fixture
def mock_openai_result(
    test_receipt_detail: ReceiptDetail,
) -> ParsedChatCompletion[ReceiptDetail]:
    return create_mock_completion(test_receipt_detail)


def test_analyze_image_success(
    mock_openai_client,
    mock_openai_result: ParsedChatCompletion[ReceiptDetail],
    test_receipt_detail: ReceiptDetail,
):
    mock_openai_client.beta.chat.completions.parse.return_value = mock_openai_result

    openai_handler = OpenAIHandler()
    result = openai_handler.analyze_image(TEST_BASE64_IMAGE, TEST_IMAGE_TYPE)

    assert result.store_name == test_receipt_detail.store_name
    assert result.date == test_receipt_detail.date
    assert result.amount == test_receipt_detail.amount
    assert result.category == test_receipt_detail.category


def test_openai_handler_initialization():
    handler = OpenAIHandler()

    assert handler.client is not None
    assert handler.client.max_retries == OpenAIHandler.MAX_RETRIES
    assert handler.MODEL == OpenAIHandler.MODEL
    assert handler.TEMPERATURE == OpenAIHandler.TEMPERATURE
    assert handler.MAX_TOKENS == OpenAIHandler.MAX_TOKENS


def test_analyze_image_response_format_error(mock_openai_client):
    mock_completion = create_mock_completion(parsed_data=None)
    mock_openai_client.beta.chat.completions.parse.return_value = mock_completion

    openai_handler = OpenAIHandler()
    with pytest.raises(OpenAIResponseFormatError) as exc_info:
        openai_handler.analyze_image(TEST_BASE64_IMAGE, TEST_IMAGE_TYPE)

    assert exc_info.type == OpenAIResponseFormatError
    assert str(exc_info.value) == "OpenAIのレスポンス形式が不正です"


@pytest.mark.parametrize(
    "exception_type, expected_exception",
    [
        (
            AuthenticationError,
            OpenAIAuthenticationError,
        ),
        (
            PermissionDeniedError,
            OpenAIAuthenticationError,
        ),
        (
            APITimeoutError,
            OpenAIServiceUnavailable,
        ),
        (
            InternalServerError,
            OpenAIServiceUnavailable,
        ),
        (
            RateLimitError,
            OpenAIServiceUnavailable,
        ),
        (
            Exception,
            OpenAIUnexpectedError,
        ),
    ],
)
def test_analyze_image_error_handling(
    mocker: MockFixture,
    mock_openai_client,
    exception_type,
    expected_exception,
) -> None:
    if exception_type is Exception:
        mock_openai_client.beta.chat.completions.parse.side_effect = exception_type(
            "予期せぬエラーが発生しました。"
        )
    elif exception_type is APITimeoutError:
        # APITimeoutErrorは異なる引数構造
        mock_openai_client.beta.chat.completions.parse.side_effect = exception_type(
            request=mocker.MagicMock()
        )
    else:
        # その他のOpenAI例外は特定の引数が必要
        mock_openai_client.beta.chat.completions.parse.side_effect = exception_type(
            message="OpenAIエラー", response=mocker.MagicMock(), body={}
        )

    openai_handler = OpenAIHandler()
    with pytest.raises(expected_exception) as exc_info:
        openai_handler.analyze_image(TEST_BASE64_IMAGE, TEST_IMAGE_TYPE)

    assert exc_info.type == expected_exception
