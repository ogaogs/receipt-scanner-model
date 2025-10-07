from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from src.receipt_scanner_model.analyze import ReceiptDetail, get_receipt_detail
from src.receipt_scanner_model.s3_client import S3Client, MAX_FILE_SIZE
from src.receipt_scanner_model.logger_config import set_logger
import tomllib
import logging
from pydantic import BaseModel, field_validator
from src.receipt_scanner_model.error import (
    ContentSizeError,
    InvalidContentTypeError,
    S3NotFound,
    S3Forbidden,
    S3ServiceUnavailable,
    S3InternalServerError,
    OpenAIAuthenticationError,
    OpenAIServiceUnavailable,
    OpenAIResponseFormatError,
    CustomHTTPException,
    ErrorCode,
)
from pathvalidate import ValidationError, validate_filename

# ログ設定を初期化
set_logger()
logger = logging.getLogger(__name__)

with open("pyproject.toml", "rb") as f:
    data = tomllib.load(f)
    version = data["project"]["version"]

app = FastAPI(version=version)


@app.exception_handler(CustomHTTPException)
async def custom_exception_handler(request: Request, exc: CustomHTTPException):
    """CustomHTTPExceptionを構造化されたエラーレスポンスに変換する"""
    return JSONResponse(
        status_code=exc.http_status_code,
        content={
            "error_type_code": exc.error_type_code.value,
            "message": exc.message,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """RequestValidationErrorをHTTPExceptionの形に変換する"""
    logger.exception("レシート解析中にエラーが起きました。")

    # Content-Typeチェック
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("application/json"):
        return JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content={
                "error_type_code": ErrorCode.CLIENT_ERROR.value,
                "message": "リクエストのContent-Typeが不正です。",
            },
        )

    error_type = exc.errors()[0]["type"]

    # フィールドの欠落やJSONの不正な場合は400 Bad Requestを返す
    if error_type in ["missing", "json_invalid"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error_type_code": ErrorCode.CLIENT_ERROR.value,
                "message": "リクエストが不正です。",
            },
        )

    raise CustomHTTPException(
        http_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_type_code=ErrorCode.CLIENT_ERROR,
        message="リクエストのバリデーションに失敗しました。入力内容を確認してください。",
    )


class FileName(BaseModel):
    filename: str

    @field_validator("filename")
    @classmethod
    def check_filename(cls, value: str) -> str:
        try:
            validate_filename(value)
            return value
        except ValidationError as e:
            logger.error(f"無効なファイル名でエラーが発生しました。 {value}: {str(e)}")
            raise ValueError(f"無効なファイル名です。 {value}: {str(e)}")


def handle_receipt_exception(e: Exception, filename: str | None):
    """例外を分類してCustomHTTPExceptionに変換する

    Args:
        e: キャッチされた例外

    Returns:
        CustomHTTPException: 構造化されたエラーレスポンスを持つCustomHTTPException
    """
    logger.exception(f"レシート解析中にエラーが起きました。ファイル名: {filename}")

    if isinstance(e, ContentSizeError):
        return CustomHTTPException(
            http_status_code=status.HTTP_400_BAD_REQUEST,
            error_type_code=ErrorCode.SIZE_ERROR,
            message=f"ダウンロードした画像サイズが0バイト以下か、{MAX_FILE_SIZE}より大きいです。ファイル名: {filename}",
        )
    if isinstance(e, InvalidContentTypeError):
        return CustomHTTPException(
            http_status_code=status.HTTP_400_BAD_REQUEST,
            error_type_code=ErrorCode.INVALID_TYPE,
            message=f"ダウンロードした画像のContent-Typeが不正です。ファイル名: {filename}",
        )
    elif isinstance(e, S3NotFound):
        return CustomHTTPException(
            http_status_code=status.HTTP_404_NOT_FOUND,
            error_type_code=ErrorCode.CLIENT_ERROR,
            message=f"指定されたファイル名({filename})が見つかりません。ファイルアップロードに問題がある可能性があります。",
        )
    elif isinstance(e, OpenAIResponseFormatError):
        return CustomHTTPException(
            http_status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_type_code=ErrorCode.SERVER_ERROR,
            message="解析結果が予期せぬ形式でした。再度解析をすることで、正常に動作する場合があります。問題が継続する場合は、サポートまでお問い合わせください。",
        )
    elif isinstance(
        e, (S3ServiceUnavailable, S3InternalServerError, OpenAIServiceUnavailable)
    ):
        return CustomHTTPException(
            http_status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_type_code=ErrorCode.SERVER_ERROR,
            message="S3またはOpenAIのサービスが一時的に利用できません。時間をおいて再度お試しください。",
        )
    elif isinstance(e, (S3Forbidden, OpenAIAuthenticationError)):
        return CustomHTTPException(
            http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type_code=ErrorCode.SERVER_ERROR,
            message="レシート解析中に権限エラーが起きました。",
        )
    else:  # S3BadRequest, OpenAIUnexpectedError, S3UnexpectedErrorを含むその他のエラー
        return CustomHTTPException(
            http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type_code=ErrorCode.SERVER_ERROR,
            message="レシート解析中にエラーが起きました。しばらくしてから再度お試しください。問題が継続する場合は、サポートまでお問い合わせください",
        )


@app.get("/")
async def root():
    """
    APIのバージョンを返す
    """
    return {"version": app.version}


@app.post("/receipt-analyze")
def receipt_analyze(body: FileName) -> ReceiptDetail:
    """S3のファイル名からレシートを解析し、ReceiptDetailを返す

    Args:
        body (FileName): ファイル名

    Returns:
        ReceiptDetail: 解析したレシート詳細
    """
    filename = None
    try:
        filename = body.filename
        # S3Clientを初期化
        s3_client = S3Client()

        # S3からファイル名を指定して画像をダウンロード
        image_bytes, content_type = s3_client.download_image_by_filename(filename)

        receipt_detail = get_receipt_detail(image_bytes, content_type)
        logger.info(receipt_detail)
        return receipt_detail
    except Exception as e:
        raise handle_receipt_exception(e, filename)
