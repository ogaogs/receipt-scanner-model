from fastapi import FastAPI, HTTPException
from src.receipt_scanner_model.analyze import ReceiptDetail, get_receipt_detail
from src.receipt_scanner_model.s3_client import S3Client
import tomllib
from pydantic import BaseModel
from src.receipt_scanner_model.error import (
    S3BadRequest,
    S3NotFound,
    S3Forbidden,
    S3ServiceUnavailable,
    S3InternalServiceError,
)

with open("pyproject.toml", "rb") as f:
    data = tomllib.load(f)
    version = data["project"]["version"]

app = FastAPI(version=version)


class FileName(BaseModel):
    filename: str


@app.get("/")
async def root():
    """
    APIのバージョンを返す
    """
    return {"version": app.version}


@app.post("/receipt-analyze")
async def receipt_analyze(request: FileName) -> ReceiptDetail:
    """S3のファイル名からレシートを解析し、ReceiptDetailを返す

    Args:
        request (FileName): ファイル名

    Returns:
        ReceiptDetail: 解析したレシート詳細
    """
    try:
        # S3Clientを初期化
        s3_client = S3Client()

        # S3からファイル名を指定して画像をダウンロード
        image_bytes = s3_client.download_image_by_filename(request.filename)

        receipt_detail = get_receipt_detail(image_bytes)
        return receipt_detail
    except (S3BadRequest, S3NotFound):
        raise HTTPException(
            status_code=400,
            detail="レシート解析中にエラーが起きました。再度レシートをアップロードしてください。",
        )
    except S3ServiceUnavailable:
        raise HTTPException(
            status_code=503,
            detail="レシート解析中にエラーが起きました。しばらくしてから再度お試しください。",
        )
    except (S3Forbidden, S3InternalServiceError):
        raise HTTPException(
            status_code=500,
            detail="レシート解析中にエラーが起きました。開発者にお問い合わせください。",
        )
    except Exception as e:
        print(f"レシート解析中にエラーが起きました: {e}")
        raise HTTPException(
            status_code=500,
            detail="レシート解析中にエラーが起きました。開発者にお問い合わせください。",
        )
