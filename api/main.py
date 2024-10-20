import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from src.receipt_scanner_model import scan_receipt, analyze
import tomllib
from pydantic import BaseModel

with open("pyproject.toml", "rb") as f:
    data = tomllib.load(f)
    version = data["project"]["version"]


class PreSignedURL(BaseModel):
    pre_signed_url: str


class Error(BaseModel):
    code: int
    message: str


class ReceiptAnalyzationResponse(BaseModel):
    receipt_detail: analyze.ReceiptDetail | None
    error: Error | None


app = FastAPI(version=version)


@app.get("/")
async def root():
    """
    APIのバージョンを返す
    """
    return {"version": app.version}


@app.post("/scan-receipt")
async def total_scan_receipt(file: UploadFile = File(...)):
    """
    レシートの合計を返す
    """
    total = scan_receipt.scan(file.file.read())["amount"]
    return {"total": total}


@app.post("/receipt-analyze")
async def receipt_analyze(request: PreSignedURL) -> ReceiptAnalyzationResponse:
    """pre_signed_urlからレシートを解析し、ReceiptDetailを返す。

    Args:
        request (PreSignedURL): ダウンロード用のpre_signed_url

    Returns:
        ReceiptAnalyzationResponse: レシートの解析結果とERROR
    """
    try:
        # S3のpre_signed_urlから画像を取得
        response = requests.get(request.pre_signed_url)
        response.raise_for_status()
        image_bytes = response.content  # バイトデータを取得

        # 画像データを解析
        receipt_detail = analyze.get_receipt_detail(image_bytes)

        return ReceiptAnalyzationResponse(receipt_detail=receipt_detail, error=None)

    except requests.exceptions.RequestException as e:
        # pre_signed_urlからの画像取得に失敗した場合
        return ReceiptAnalyzationResponse(
            receipt_detail=None,
            error=Error(code=400, message=f"Failed to download image: {e}"),
        )

    except Exception as e:
        # その他のエラー
        raise HTTPException(status_code=500, detail=f"Error analyzing receipt: {e}")
