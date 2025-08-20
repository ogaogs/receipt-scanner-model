# receipt-scanner-model

レシート画像を解析する API を管理するリポジトリ

## 何のためのリポジトリか

[家計簿くん](https://github.com/AyumuOgasawara/receipt-scanner)でレシートを解析する機能がある。<br>
その機能にこのリポジトリの API が使用されている。<br>
レシート画像から`店名`、`合計金額`、`購入日付`、`出費のカテゴリ`を抽出することができる。

## API のエンドポイント

| メソッド |  エンドポイント  |         リクエスト |                       リスポンス |
| :------- | :--------------: | -----------------: | -------------------------------: |
| GET      |        /         |                  - |                {version: string} |
| POST     | /receipt-analyze | {filename: string} | {receipt-detail : ReceiptDetail} |

※ReceiptDetail は以下の通りである。

```python
from typing import TypedDict

class ReceiptDetail(TypedDict):
    store_name: str | None
    amount: int
    date: str | None
    category: str | None
```

## 必要要件

- [Rye](https://rye.astral.sh/) >= 0.42.0 を使用した環境設定

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

- [Tesseract](https://tesseract-ocr.github.io/tessdoc/Installation.html) = 5.5.0 のインストール
  - `Homebrew`の場合
    ```sh
    brew install tesseract
    ```

## 使用方法

### 環境変数

`.env.templete`を参考に`.env`ファイルを作成し、以下の環境変数を設定してください：

```sh
# .envファイルを作成
cp .env.templete .env
```

`.env`ファイルの内容：

```
BUCKET_NAME=receipt-scanner-v1
AWS_ACCESS_KEY_ID=<AWSアクセスキー>
AWS_SECRET_ACCESS_KEY=<AWSシークレットキー>
AWS_DEFAULT_REGION=ap-northeast-1
OPENAI_API_KEY=<OpenAIのAPIキー>
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

- カバレッジ付きテスト実行

  ```sh
  # c1のカバレッジを測定
  coverage run --branch -m pytest tests
  coverage report --show-missing --include="api/*,src/*"
  ```

  - `tests/test_api`
    API に関するテスト
  - `tests/test_src`
    src 下のコードに関するテスト
