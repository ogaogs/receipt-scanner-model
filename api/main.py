from fastapi import FastAPI, UploadFile, File
from src.receipt_scanner_model import scan_receipt
import tomllib

with open("pyproject.toml", "rb") as f:
    data = tomllib.load(f)
    version = data["project"]["version"]

app = FastAPI(version=version)


@app.get("/")
async def root():
    """
    APIのバージョンを返す
    """
    return {"version": app.version}


@app.post("/scan-receipt")
async def receipt_analyze(file: UploadFile = File(...)):
    """
    レシートの合計を返す
    """
    total = scan_receipt.scan(file.file.read())["amount"]
    return {"total": total}
