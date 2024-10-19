from pydantic import BaseModel
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from typing import TypedDict


class ReceiptExtraction(BaseModel):
    store_name: str | None
    date: str | None
    category: str | None


class GPTResult(TypedDict):
    status: bool
    content: str | ReceiptExtraction | None


client = OpenAI()

MODEL = "gpt-4o-mini"
TEMPERATURE = 1
MAX_TOKENS = 2000


def completion(system_prompt: str, user_prompt: str) -> GPTResult:
    """GPTからレシートの「店名」「日付」「カテゴリー」を取得する

    Args:
        system_prompt (str): システムプロンプト
        user_prompt (str): ユーザープロンプト

    Returns:
        GPTResult: 実行結果のステータス、実行結果 | エラーメッセージ
    """
    messages: list[ChatCompletionMessageParam] = []
    system_prompt_message: ChatCompletionSystemMessageParam = {
        "role": "system",
        "content": system_prompt,
    }
    messages.append(system_prompt_message)

    user_prompt_message: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": user_prompt,
    }
    messages.append(user_prompt_message)

    try:
        response = client.beta.chat.completions.parse(
            model=MODEL,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            response_format=ReceiptExtraction,
        )
        return {"status": True, "content": response.choices[0].message.parsed}
    except Exception as e:
        return {"status": False, "content": str(e)}
