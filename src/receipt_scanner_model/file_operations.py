import boto3
import io

BUCKET_NAME = "receipt-scaner"

s3 = boto3.client("s3")


def download_img_to_bytes(img_name: str) -> bytes:
    """s3からファイルをダウンロードし、bytesで返す

    Args:
        img_name (str): s3に保存されているファイル名

    Returns:
        bytes: bytesに変換されたファイル
    """
    # メモリ上のバッファを作成
    img_data = io.BytesIO()

    # S3から画像をダウンロードし、バッファに書き込む
    s3.download_fileobj(BUCKET_NAME, img_name, img_data)

    # バッファの先頭にカーソルを戻す
    img_data.seek(0)

    # bytesデータを取得
    return img_data.getvalue()
