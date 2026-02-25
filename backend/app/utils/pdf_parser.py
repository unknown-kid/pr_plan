import pdfplumber
from typing import Iterator, Dict, Optional
import os
import re


class StreamingPDFParser:
    """流式PDF解析器 - 内存优化"""

    def __init__(self, pdf_path: str, chunk_size: int = 1000):
        self.pdf_path = pdf_path
        self.chunk_size = chunk_size

    def extract_text_by_page(self) -> Iterator[Dict]:
        """按页提取PDF文本"""
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")

        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if not text:
                    continue
                yield {"text": text, "page": page_num}

    def extract_chunks(self) -> Iterator[Dict]:
        """
        流式提取PDF文本块
        避免一次性加载整个PDF到内存
        """
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if not text:
                    continue

                # 分块处理 (按中英文标点和长度分块)
                normalized = re.sub(r"\s+", " ", text).strip()
                sentences = re.split(r"(?<=[。！？.!?])\s+", normalized)
                current_chunk = []
                current_length = 0

                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    sentence = sentence + " "
                    if current_length + len(sentence) > self.chunk_size:
                        if current_chunk:
                            yield {
                                "text": "".join(current_chunk),
                                "page": page_num,
                                "chunk_index": f"{page_num}_{len(current_chunk)}",
                            }
                            current_chunk = []
                            current_length = 0

                    current_chunk.append(sentence)
                    current_length += len(sentence)

                # 处理页内最后一块
                if current_chunk:
                    yield {
                        "text": "".join(current_chunk),
                        "page": page_num,
                        "chunk_index": f"{page_num}_{len(current_chunk)}",
                    }

    def get_metadata(self) -> Dict:
        """获取PDF基本信息"""
        with pdfplumber.open(self.pdf_path) as pdf:
            return {"total_pages": len(pdf.pages), "metadata": pdf.metadata}
