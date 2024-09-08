from fastapi import FastAPI
from src.receipt_scanner_model import analyze
from pydantic import BaseModel
import tomllib


# TODO: fileの型をbytesに変更する
class Receipt(BaseModel):
    file: str


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


@app.post("/receipt-analyze")
async def receipt_analyze(receipt: Receipt):
    """
    レシートの合計を返す
    """
    total = analyze.main(receipt.file)
    return {"total": total}
