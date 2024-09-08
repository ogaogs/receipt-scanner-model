from fastapi import FastAPI
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
