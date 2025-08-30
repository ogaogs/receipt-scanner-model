from src.receipt_scanner_model.setting import setting
from pydantic import BaseModel, Field
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from openai import (
    APITimeoutError,
    PermissionDeniedError,
    InternalServerError,
    RateLimitError,
    AuthenticationError,
)
from src.receipt_scanner_model.error import (
    OpenAIAuthenticationError,
    OpenAIServiceUnavailable,
    OpenAIUnexpectedError,
    OpenAIResponseFormatError,
)
import logging

logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class ReceiptDetail(BaseModel):
    store_name: str | None = Field(description="買い物をした店名")
    date: str | None = Field(description="買い物をした日付")
    amount: int | None = Field(description="買い物の合計金額")
    category: str | None = Field(description="買い物のカテゴリー")


SYSTEM_PROMPT = """
あなたは家計簿アプリのレシート解析AIです。
与えられる画像はレシートの写真です。以下の情報を抽出してください。

## store_name
レシートより買い物した店名を取得してください。不自然なスペースがある際はスペースを削除してください。
上に記載されることが多いです。取得できない場合は None としてください。

## amount
レシートより、買い物の合計金額を数字で取得してください。買い物の合計金額は通常レシートの下側に書かれることが多いです。
取得できない場合は None としてください。

## date
レシート画像より、買い物を行なった日付を"YYYY/MM/DD"の形式で取得してください。
商品の上に記載されることが多いです。取得できない場合は None としてください。

## category
レシートの内容を確認し、買い物のカテゴリーで最も適切なカテゴリーを以下の中から選択してください。
カテゴリー：["食費"、"水道光熱費"、"家賃"、"娯楽"、"衣服・美容"、"日用品"、"病院代"、"交通費"、"その他"]
取得できない場合は None としてください。
"""


def openai_error_handling(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except OpenAIResponseFormatError:
            raise
        except (AuthenticationError, PermissionDeniedError) as e:
            logger.error(f"OpenAIの認証エラー: {str(e)}")
            raise OpenAIAuthenticationError(
                401, "OpenAIの認証に失敗しました。APIキーを確認してください。"
            )
        except (
            APITimeoutError,
            RateLimitError,
            InternalServerError,
        ) as e:
            logger.error(f"OpenAIの一時的なエラー: {str(e)}")
            raise OpenAIServiceUnavailable(
                503,
                "OpenAIのサービスが一時的に利用できません。時間をおいて再度お試しください。",
            )
        except Exception as e:
            logger.error(f"OpenAIの予期しないエラー: {str(e)}")
            raise OpenAIUnexpectedError(500, "OpenAIの予期しないエラーが発生しました。")

    return wrapper


class OpenAIHandler:
    MODEL = "gpt-4o-mini"
    TEMPERATURE = 0
    MAX_TOKENS = 16384
    MAX_RETRIES = 3

    def __init__(self):
        self.client = OpenAI(
            api_key=setting.openai_api_key, max_retries=OpenAIHandler.MAX_RETRIES
        )

    @openai_error_handling
    def analyze_image(self, base64_image: str, image_type: str) -> ReceiptDetail:
        """OpenAIのAPIを呼び出し、レシートの解析を行う

        Args:
            base64_image (str): Base64エンコードされた画像データ
            image_type (str): 画像のMIMEタイプ（例: "jpeg", "png"）
        Returns:
            ReceiptDetail: 解析されたレシートの詳細情報
        """
        messages: list[ChatCompletionMessageParam] = []
        system_prompt_message: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
        messages.append(system_prompt_message)

        user_prompt_message: ChatCompletionUserMessageParam = {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{image_type};base64,{base64_image}"
                    },
                }
            ],
        }
        messages.append(user_prompt_message)
        response = self.client.beta.chat.completions.parse(
            model=OpenAIHandler.MODEL,
            messages=messages,
            response_format=ReceiptDetail,
        )
        output = response.choices[0].message.parsed
        if not isinstance(output, ReceiptDetail):
            raise OpenAIResponseFormatError(
                code=503, message="OpenAIの応答の解析に失敗しました。"
            )
        return output
