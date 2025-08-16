"""S3からの画像ダウンロード処理を担当するクライアント"""

import boto3
import io
import logging
from src.receipt_scanner_model.setting import setting
from botocore.exceptions import ClientError
from src.receipt_scanner_model.error import (
    S3BadRequest,
    S3NotFound,
    S3Forbidden,
    S3ServiceUnavailable,
    S3InternalServiceError,
)

logger = logging.getLogger(__name__)


class S3Client:
    """S3からの画像ダウンロードを行うクライアント"""

    def __init__(self) -> None:
        self.bucket_name = setting.bucket_name

        self.s3_client = boto3.client(
            "s3",
            region_name=setting.aws_default_region,
            aws_access_key_id=setting.aws_access_key_id,
            aws_secret_access_key=setting.aws_secret_access_key,
        )

    def download_image_by_filename(self, filename: str) -> bytes:
        """S3からファイル名を指定して画像をダウンロードする

        Args:
            filename: S3のオブジェクトキー（ファイル名）

        Returns:
            bytes: ダウンロードした画像
        """
        file_obj = None
        try:
            # メモリ上にファイルオブジェクトを作成
            file_obj = io.BytesIO()

            # S3からファイルをダウンロード
            self.s3_client.download_fileobj(self.bucket_name, filename, file_obj)

            # バイナリデータを取得
            file_obj.seek(0)
            image_bytes = file_obj.getvalue()

            return image_bytes

        except ClientError as e:
            error_message = e.response["Error"]["Message"]
            http_status_code = int(
                e.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 500)
            )

            if http_status_code == 400:
                logger.error(
                    f"ダウンロード中にエラーが起きました: {http_status_code} {error_message}"
                )
                raise S3BadRequest(
                    http_status_code,
                    f"ダウンロード中にエラーが起きました: {error_message}",
                )
            elif http_status_code == 404:
                logger.error(
                    f"ダウンロード中にエラーが起きました: {http_status_code} {error_message}"
                )
                raise S3NotFound(
                    http_status_code,
                    f"ダウンロード中にエラーが起きました: {error_message}",
                )
            elif http_status_code == 403:
                logger.error(
                    f"アクセスが拒否されました: {http_status_code} {error_message}"
                )
                raise S3Forbidden(
                    http_status_code,
                    f"アクセスが拒否されました: {error_message}",
                )
            elif http_status_code == 503:
                logger.error(
                    f"ダウンロード中に予期しないエラーが発生しました: {http_status_code} {error_message}"
                )
                raise S3ServiceUnavailable(
                    http_status_code,
                    f"ダウンロード中に予期しないエラーが発生しました: {error_message}",
                )
            else:
                logger.error(
                    f"ダウンロード中に予期しないエラーが発生しました: {http_status_code} {error_message}"
                )
                raise S3InternalServiceError(
                    http_status_code,
                    f"ダウンロード中に予期しないエラーが発生しました: {error_message}",
                )
        except Exception as e:
            logger.error(f"ダウンロード中に予期しないエラーが発生しました: {e}")
            raise S3InternalServiceError(
                500, f"ダウンロード中に予期しないエラーが発生しました: {e}"
            )

        finally:
            # ファイルオブジェクトをクリーンアップ
            if "file_obj" in locals() and file_obj:
                file_obj.close()
