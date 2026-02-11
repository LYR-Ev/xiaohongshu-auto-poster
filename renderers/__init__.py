"""唯一发帖格式出口：Renderer 决定最终文案结构，Prompt/Parser 只提供素材。"""
from .xhs_word_renderer import render_xhs_word_post, WordPost

__all__ = ["render_xhs_word_post", "WordPost"]
