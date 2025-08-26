import base64


def encode_image(image_bytes: bytes):
    """画像のバイトデータをBase64エンコードする
    Args:
        image_bytes (bytes): 画像のバイトデータ

    Returns: str: Base64エンコードされた画像データ
    """
    return base64.b64encode(image_bytes).decode("utf-8")
