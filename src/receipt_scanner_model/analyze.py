from src.receipt_scanner_model.open_ai import OpenAIHandler, ReceiptDetail
from src.receipt_scanner_model.file_operations import encode_image


def get_receipt_detail(img_bytes: bytes, content_type: str) -> ReceiptDetail:
    """レシートの解析を行い、ReceiptDetailを返す

    Args:
        img_bytes (bytes): ダウンロードした画像のバイトデータ
        content_type (str): コンテントのMIMEタイプ（例: "image/jpeg", "image/png"）

    Returns:
        ReceiptDetail: 店名、金額、日付、カテゴリー
    """
    openai_handler = OpenAIHandler()
    base64_image = encode_image(img_bytes)
    return openai_handler.analyze_image(base64_image, content_type)
