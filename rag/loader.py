"""通用文档加载器：支持 PDF / DOCX / TXT"""
from pathlib import Path

import fitz
from docx import Document


def load_document(path: str) -> str:
    """根据文件扩展名选择合适的加载方式"""
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return _load_pdf(path)
    elif suffix in (".doc", ".docx"):
        return _load_docx(path)
    elif suffix == ".txt":
        return _load_txt(path)
    else:
        raise ValueError(f"不支持的文件格式: {suffix}")


def _load_pdf(path: str) -> str:
    doc = fitz.open(path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text


def _load_docx(path: str) -> str:
    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def _load_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()
