import os
import requests


def generate_text(prompt: str, temperature: float = 0.7) -> str:
    """
    使用本地 Ollama Chat API 生成文本。

    保持原有接口：接收单个 prompt 字符串，上层无需改动。
    """
    url = os.getenv("OLLAMA_CHAT_URL", "http://localhost:11434/v1/chat/completions")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

    messages = [
        {
            "role": "user",
            "content": prompt,
        }
    ]

    resp = requests.post(
        url,
        json={
            "model": model,
            "messages": messages,
            "temperature": float(temperature),
            "stream": False,
        },
        timeout=120,
    )
    # 如果 Ollama 未启动，将抛出 ConnectionError，按你的要求不吞掉这个错误
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]
