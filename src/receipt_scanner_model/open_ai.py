from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from typing import TypedDict


class GPTResult(TypedDict):
    status: bool
    content: str | None


client = OpenAI()

MODEL = "gpt-4o-mini"
TEMPERATURE = 1
MAX_TOKENS = 2000


def completion(system_prompt: str, user_prompt: str) -> GPTResult:
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
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        return {"status": True, "content": response.choices[0].message.content}
    except Exception as e:
        return {"status": False, "content": str(e)}
