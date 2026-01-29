"""
结构化帖子解析器基类
为 word / phrase / grammar 等不同类型的内容提供统一的解析框架
"""
import re
from typing import Dict, List, Tuple, Optional, Any
from abc import ABC, abstractmethod


class StructuredPostParser(ABC):
    """
    结构化帖子解析器基类。
    子类只需定义 sections（段落标记列表），即可复用解析逻辑。
    """
    
    # 子类必须定义段落标记列表，按顺序
    sections: Tuple[str, ...] = ()
    
    def parse(self, text: str, **kwargs: Any) -> Dict[str, Any]:
        """
        解析结构化文本，提取各段落内容。
        
        Args:
            text: LLM 输出的结构化文本
            **kwargs: 额外参数（如 word、level 等，用于兜底值）
        
        Returns:
            解析后的字典，包含各段落内容
        """
        parsed_sections = {}
        
        # 提取各段落
        for mark in self.sections:
            start = text.find(mark)
            if start == -1:
                continue
            start += len(mark)
            rest = text[start:]
            end = len(rest)
            
            # 找到下一个段落标记的位置
            for next_mark in self.sections:
                if next_mark == mark:
                    continue
                j = rest.find(next_mark)
                if j != -1 and j < end:
                    end = j
            
            parsed_sections[mark] = rest[:end].strip()
        
        # 调用子类的后处理逻辑
        return self._post_process(parsed_sections, **kwargs)
    
    @abstractmethod
    def _post_process(self, sections: Dict[str, str], **kwargs: Any) -> Dict[str, Any]:
        """
        子类实现：将解析出的段落转换为业务需要的格式。
        
        Args:
            sections: 解析出的各段落内容字典 {标记: 内容}
            **kwargs: 额外参数
        
        Returns:
            业务格式的字典
        """
        pass
    
    def extract_tags(self, tags_section: str) -> List[str]:
        """
        从【标签】段落提取标签列表。
        
        Args:
            tags_section: 【标签】段落的内容
        
        Returns:
            标签列表
        """
        tags = re.findall(r"#([^#\s]+)", tags_section)
        return tags[:8]  # 限制最多8个标签
    
    def extract_meta(self, meta_section: str) -> Optional[Dict[str, str]]:
        """
        从【meta】段落提取元信息。
        
        Args:
            meta_section: 【meta】段落的内容
        
        Returns:
            元信息字典，如 {"prompt": "word_learning_v1"}
        """
        if not meta_section:
            return None
        
        meta = {}
        # 解析 prompt=word_learning_v1 格式
        for line in meta_section.split('\n'):
            line = line.strip()
            if '=' in line:
                key, value = line.split('=', 1)
                meta[key.strip()] = value.strip()
        
        return meta if meta else None
