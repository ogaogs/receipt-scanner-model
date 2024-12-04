# receipt-scanner-model

レシート画像を解析する API を管理するリポジトリ

## 何のためのリポジトリか

[家計簿くん](https://github.com/AyumuOgasawara/receipt-scanner)でレシートを解析する機能がある。<br>
その機能にこのリポジトリの API が使用されている。<br>
レシート画像から`店名`、`合計金額`、`購入日付`、`出費のカテゴリ`を抽出することができる。

## API のエンドポイント

| メソッド |  エンドポイント  |               リクエスト |                       リスポンス |
| :------- | :--------------: | -----------------------: | -------------------------------: |
| POST     | /receipt-analyze | {pre_signed_url: string} | {receipt-detail : ReceiptDetail} |

※REceiptDetail は以下の通りである。

```python
from typing import TypedDict

class ReceiptDetail(TypedDict):
    store_name: str | None
    amount: int
    date: str | None
    category: str | None
```

## 必要要件

- [Rye](https://rye.astral.sh/)を使用した環境設定

  - [仮想環境の作成](https://rye.astral.sh/guide/basics/#first-sync)＊`Rye`をインストールしていない方は[こちら](https://rye.astral.sh/guide/installation/)<br>
    ```sh
    rye sync
    ```

- pre-commit の設定

  - pre-commit のインストール
    ```sh
    # 下記の実行により、コミット時にpre-commitが実行される
    rye run pre-commit install
    ```

- [tesseract](https://tesseract-ocr.github.io/tessdoc/Installation.html)のインストール
  - `Homebrew`の場合
    ```sh
    brew install tesseract
    ```

## 技術スタック

| 技術/ライブラリ                                          | バージョン   | 説明                                 |
| -------------------------------------------------------- | ------------ | ------------------------------------ |
| [Tesseract](https://github.com/tesseract-ocr/tesseract)  | = 5.5.0      | OCR ライブラリ                       |
| [Python](https://www.python.org/)                        | >= 3.11      | Python                               |
| [Pillow](https://pypi.org/project/pillow/)               | >= 10.4.0    | 画像処理ライブラリ                   |
| [OpenCV-Python](https://pypi.org/project/opencv-python/) | >= 4.10.0.84 | コンピュータビジョンライブラリ       |
| [PyTesseract](https://pypi.org/project/pytesseract/)     | >= 0.3.13    | OCR（光学文字認識）ライブラリ        |
| [FastAPI](https://fastapi.tiangolo.com/ja/)              | >= 0.114.0   | Python Web フレームワーク            |
| [Uvicorn](https://www.uvicorn.org/)                      | >= 0.30.6    | ASGI Web サーバー                    |
| [Python-Multipart](https://multipart.fastapiexpert.com/) | >= 0.0.9     | マルチパートファイルアップロード対応 |
| [OpenAI](https://openai.com/index/openai-api/)           | >= 1.51.2    | OpenAI API クライアント              |
| [Boto3](https://aws.amazon.com/jp/sdk-for-python/)       | >= 1.35.42   | AWS SDK for Python                   |
| [Requests](https://pypi.org/project/requests/)           | >= 2.32.3    | HTTP リクエストライブラリ            |

## 開発用ライブラリ

| 技術/ライブラリ                                         | バージョン | 説明                 |
| ------------------------------------------------------- | ---------- | -------------------- |
| [Ruff](https://docs.astral.sh/ruff/)                    | >= 0.5.7   | Python リントツール  |
| [Pyright](https://microsoft.github.io/pyright/#/)       | >= 1.1.378 | 型チェックツール     |
| [Pre-commit](https://pre-commit.com/)                   | >= 3.8.0   | コード品質ツール     |
| [Pytest](https://docs.pytest.org/en/stable/index.html#) | >= 8.3.2   | テストフレームワーク |

## 使用方法

### 環境変数

GPT モデルを使用するため[OpenAI API](https://openai.com/index/openai-api/)の API キーが必要

```sh
export OPENAI_API_KEY="<OpenAIのAPIキー>"
```

### 実行方法

- 以下のコマンドで http://localhost:8000 で実行される

```sh
uvicorn api.main:app --reload
```

### Docker

- 以下のコマンドで http://localhost:8000 で実行される

```sh
docker build . -t receipt-scanner-model --build-arg PYTHON_VERSION="$(cat .python-version)"

docker run -p 127.0.0.1:8000:8000 -e OPENAI_API_KEY receipt-scanner-model
```

## 開発者向け

### Rye

プロジェクト管理に[Rye](https://rye.astral.sh/)を使用している。<br>

[Rye の基本操作](https://rye.astral.sh/guide/basics/)

- 依存関係を変更した際、その都度実行する
  ```sh
  rye sync
  ```
- [依存関係の追加](https://rye.astral.sh/guide/basics/#adding-dependencies)
  ```sh
  rye add "flask>=2.0"
  ```
- [依存関係の削除](https://rye.astral.sh/guide/basics/#remove-a-dependency)
  ```sh
  rye remove flask
  ```

### テスト実行方法

- 以下のコマンドでテストを実行する

  ```sh
  pytest tests
  ```

  - `tests/test_api`
    API に関するテスト
  - `tests/test_src`
    src 下のコードに関するテスト
