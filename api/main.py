from fastapi import FastAPI, HTTPException
from src.receipt_scanner_model.analyze import ReceiptDetail, get_receipt_detail
from src.receipt_scanner_model.s3_client import S3Client
from src.receipt_scanner_model.logger_config import set_logger
import tomllib
import logging
from pydantic import BaseModel
from src.receipt_scanner_model.error import (
    S3BadRequest,
    S3NotFound,
    S3Forbidden,
    S3ServiceUnavailable,
    S3InternalServiceError,
)

# ログ設定を初期化
set_logger()
logger = logging.getLogger(__name__)

with open("pyproject.toml", "rb") as f:
    data = tomllib.load(f)
    version = data["project"]["version"]

app = FastAPI(version=version)


class FileName(BaseModel):
    filename: str


def handle_receipt_exception(e: Exception, filename: str | None):
    """例外を分類してHTTPExceptionに変換する

    Args:
        e: キャッチされた例外

    Returns:
        HTTPException: 適切なステータスコードとメッセージを持つHTTPException
    """
    logger.exception(f"レシート解析中にエラーが起きました。ファイル名: {filename}")

    if isinstance(e, (S3BadRequest, S3NotFound)):
        return HTTPException(
            status_code=400,
            detail="レシート解析中にエラーが起きました。再度レシートをアップロードしてください。",
        )
    elif isinstance(e, S3ServiceUnavailable):
        return HTTPException(
            status_code=503,
            detail="レシート解析中にエラーが起きました。しばらくしてから再度お試しください。",
        )
    elif isinstance(e, (S3Forbidden, S3InternalServiceError)):
        return HTTPException(
            status_code=500,
            detail="レシート解析中にエラーが起きました。開発者にお問い合わせください。",
        )
    else:
        return HTTPException(
            status_code=500,
            detail="レシート解析中にエラーが起きました。開発者にお問い合わせください。",
        )


@app.get("/")
async def root():
    """
    APIのバージョンを返す
    """
    return {"version": app.version}


@app.post("/receipt-analyze")
def receipt_analyze(request: FileName) -> ReceiptDetail:
    """S3のファイル名からレシートを解析し、ReceiptDetailを返す

    Args:
        request (FileName): ファイル名

    Returns:
        ReceiptDetail: 解析したレシート詳細
    """
    filename = None
    try:
        filename = request.filename
        # S3Clientを初期化
        s3_client = S3Client()

        # S3からファイル名を指定して画像をダウンロード
        image_bytes = s3_client.download_image_by_filename(request.filename)

        receipt_detail = get_receipt_detail(image_bytes)
        return receipt_detail
    except Exception as e:
        raise handle_receipt_exception(e, filename)
