from src.receipt_scanner_model import analyze, parse_bytes, open_ai


IMAGE = "/Users/ayumu/my-projects/receipt-scanner-model/raw/book-off.png"
SYSTEM_PROMPT = """
あなたはレシートのテキストから家計簿をつけるロボットです。
レシートのテキストが与えられます。以下を取得してください。

## 取得する項目
- 買い物した店名
- 買い物した日付
- 買い物のカテゴリー

買い物のカテゴリーは以下の中から最も適切なカテゴリーを選択してください。
カテゴリー：["食費"、"水道光熱費"、"家賃"、"娯楽"、"衣服・美容"、"日用品"、"病院代"、"交通費"、"その他"]

与えられたレシートのテキストから以下の項目を取得し、出力項目に沿って教えてください。

## カテゴリー
取得したカテゴリーを教えてください。

## 店名
取得した店名を教えてください。

## 日付
取得した日付を教えてください。

"""


def get_receipt_detail(image: str):
    img_bytes = parse_bytes.imgstr_to_bytes(IMAGE)
    analyzed_date = analyze.scan(img_bytes)
    result = open_ai.completion(SYSTEM_PROMPT, analyzed_date["text"])
    print(result["content"])


get_receipt_detail(IMAGE)
