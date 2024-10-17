from src.receipt_scanner_model import analyze, open_ai, file_operations
from typing import TypedDict


class ReceiptDetail(TypedDict):
    store_name: str | None
    amount: int
    date: str | None
    category: str | None


SYSTEM_PROMPT = """
あなたはレシートのテキストから家計簿をつけるロボットです。
与えられるデータはレシートをOCRしたテキストデータです。
以下の項目を抽出してください。

## category
買い物のカテゴリーは以下の中から最も適切なカテゴリーを選択してください。
カテゴリー：["食費"、"水道光熱費"、"家賃"、"娯楽"、"衣服・美容"、"日用品"、"病院代"、"交通費"、"その他"]
取得できない場合は None としてください。

## store_name
取得した店名を取得してください。不自然なスペースがある際はスペースを削除してください。
上に記載されることが多いです。取得できない場合は None としてください。

## date
取得した日付を"YYYY/MM/DD"の形式で取得してください。
商品の上に記載されることが多いです。取得できない場合は None としてください。

"""


def get_receipt_detail(image: str) -> ReceiptDetail:
    """レシートの解析を行い、ReceiptDetailを返す

    Args:
        image (str): s3上のファイル名

    Returns:
        ReceiptDetail: 店名、金額、日付、カテゴリー
    """
    img_bytes = file_operations.download_img_to_bytes(image)
    analyzed_date = analyze.scan(img_bytes)
    result = open_ai.completion(SYSTEM_PROMPT, analyzed_date["text"])
    content = result["content"]
    if not result["status"]:
        print(content)

    if isinstance(content, open_ai.ReceiptExtraction):
        return {
            "store_name": content.store_name,
            "amount": analyzed_date["amount"],
            "date": content.date,
            "category": content.category,
        }
    else:
        return {"store_name": None, "amount": 0, "date": None, "category": None}
