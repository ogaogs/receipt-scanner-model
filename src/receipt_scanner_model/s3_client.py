"""S3からの画像ダウンロード処理を担当するクライアント"""

import boto3
import logging
from src.receipt_scanner_model.setting import setting
from botocore.exceptions import ClientError
from src.receipt_scanner_model.error import (
    S3BadRequest,
    S3NotFound,
    S3Forbidden,
    S3ServiceUnavailable,
    S3InternalServerError,
    S3UnexpectedError,
)

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


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

    def download_image_by_filename(
        self, filename: str, max_size: int = MAX_FILE_SIZE
    ) -> tuple[bytes, str]:
        """S3からファイル名を指定して画像をダウンロードする

        Args:
            filename: S3のオブジェクトキー（ファイル名）

        Returns:
            bytes: ダウンロードした画像
            str: コンテントのMIMEタイプ（例: "image/jpeg", "image/png"）
        """
        try:
            # まずheadでファイルサイズを確認
            head_response = self.s3_client.head_object(
                Bucket=self.bucket_name, Key=filename
            )
            content_length = head_response.get("ContentLength", 0)

            if content_length <= 0:
                logger.error(f"ファイルサイズが0バイト以下です: {content_length} bytes")
                raise S3BadRequest(
                    400, f"ファイルサイズが0バイト以下です: {content_length} bytes"
                )
            elif content_length > max_size:
                logger.error(
                    f"ファイルサイズが制限を超えています: {content_length} bytes"
                )
                raise S3BadRequest(
                    400, f"ファイルサイズが制限を超えています: {content_length} bytes"
                )

            content_type = head_response.get("ContentType", None)

            if content_type is None or not content_type.startswith("image/"):
                logger.error(
                    f"ファイルのContent-Typeが画像ではありません: {content_type}"
                )
                raise S3BadRequest(
                    400, f"ファイルのContent-Typeが画像ではありません: {content_type}"
                )
            if content_type not in ["image/png", "image/jpeg"]:
                logger.error(f"サポートされていない画像形式です: {content_type}")
                raise S3BadRequest(
                    400, f"サポートされていない画像形式です: {content_type}"
                )

            # サイズ・画像タイプに問題なければダウンロード
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=filename)
            with response["Body"] as stream:
                return stream.read(), content_type

        except ClientError as e:
            error_message = e.response["Error"]["Message"]
            http_status_code = int(
                e.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 500)
            )

            if http_status_code == 400:
                logger.error(
                    f"不正なリクエストです: {http_status_code} {error_message}"
                )
                raise S3BadRequest(
                    http_status_code,
                    f"不正なリクエストです: {error_message}",
                )
            elif http_status_code == 404:
                logger.error(
                    f"指定されたファイルがS3にありません: {http_status_code} {error_message}"
                )
                raise S3NotFound(
                    http_status_code,
                    f"指定されたファイルがS3にありません: {error_message}",
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
                    f"S3サービスが一時的に利用できません: {http_status_code} {error_message}"
                )
                raise S3ServiceUnavailable(
                    http_status_code,
                    f"S3サービスが一時的に利用できません: {error_message}",
                )
            elif http_status_code == 500:
                logger.error(
                    f"S3サービスでInternalServerErrorが発生しました: {http_status_code} {error_message}"
                )
                raise S3InternalServerError(
                    http_status_code,
                    f"S3サービスでInternalServerErrorが発生しました: {error_message}",
                )
            else:
                logger.error(
                    f"ダウンロード中に予期しないエラーが発生しました: {http_status_code} {error_message}"
                )
                raise S3UnexpectedError(
                    http_status_code,
                    f"ダウンロード中に予期しないエラーが発生しました: {error_message}",
                )
        except S3BadRequest:
            raise
        except Exception as e:
            logger.error(f"ダウンロード中に予期しないエラーが発生しました: {e}")
            raise S3UnexpectedError(
                500, f"ダウンロード中に予期しないエラーが発生しました: {e}"
            )
