"""
Ollama 可用性检查脚本（推荐在开发/调试时先跑一下）
"""
import requests


def check_ollama(url: str = "http://localhost:11434") -> bool:
    """
    检查本地 Ollama 是否可用。

    Args:
        url: Ollama 服务地址（默认 http://localhost:11434）

    Returns:
        True 表示可用，False 表示不可用
    """
    try:
        r = requests.get(f"{url}/api/tags", timeout=5)
        r.raise_for_status()
        print("✅ Ollama 正在运行")
        return True
    except Exception as e:
        print("❌ Ollama 不可用：", e)
        return False


if __name__ == "__main__":
    check_ollama()
