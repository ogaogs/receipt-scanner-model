from fastapi import FastAPI, UploadFile, File
from src.receipt_scanner_model import analyze
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


@app.post("/receipt-analyze")
async def receipt_analyze(file: UploadFile = File(...)):
    """
    レシートの合計を返す
    """
    total = analyze.main(file.file.read())
    return {"total": total}
