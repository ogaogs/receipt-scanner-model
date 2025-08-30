from src.receipt_scanner_model.open_ai import OpenAIHandler, ReceiptDetail
from src.receipt_scanner_model.file_operations import encode_image


def get_receipt_detail(img_bytes: bytes, image_type: str) -> ReceiptDetail:
    """レシートの解析を行い、ReceiptDetailを返す

    Args:
        img_bytes (bytes): ダウンロードした画像のバイトデータ
        image_type (str): 画像のMIMEタイプ（例: "jpeg", "png"）

    Returns:
        ReceiptDetail: 店名、金額、日付、カテゴリー
    """
    openai_handler = OpenAIHandler()
    base64_image = encode_image(img_bytes)
    return openai_handler.analyze_image(base64_image, image_type)
