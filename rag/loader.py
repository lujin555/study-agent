"""通用文档加载器：支持 PDF / DOCX / TXT / Markdown（扫描版 PDF 可开启 OCR）"""
import re
from pathlib import Path

import pymupdf as fitz  # fitz 是 PyMuPDF 的旧名，新版叫 pymupdf
from docx import Document

from config import OCR_ENABLED, OCR_MIN_SCORE, OCR_MIN_LINE_LEN

# 判定一页"有实质文字"的最小字符数（低于此值视为图片页/空白页/水印页）
MIN_CHARS_PER_PAGE = 50
# 有效页占比低于此值，判定整份 PDF 为扫描版（无文字层）
SCAN_PAGE_RATIO = 0.1


class ScanPDFError(ValueError):
    """扫描版 PDF：没有文字层，RAG 无法直接提取内容。

    抛出这个异常而不是返回空字符串，是为了让上层能明确告诉用户
    「这份 PDF 是扫描版，内容没有进知识库」，
    避免出现「看起来入库成功、实际只捞到几个字」的静默失效。
    """

    def __init__(self, path: str, total: int, valid: int, chars: int = 0):
        self.path = path
        self.total = total
        self.valid = valid
        self.chars = chars
        name = Path(path).name
        super().__init__(
            f"扫描版 PDF：{name} 共 {total} 页，其中只有 {valid} 页有文字"
            f"（可提取字符共 {chars} 个），没有文字层，无法直接检索。"
            f"请换一份带文字层的电子版 PDF，或先做 OCR 识别后再上传。"
        )


def load_document(path: str) -> str:
    """根据文件扩展名选择合适的加载方式"""
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return _load_pdf(path)
    elif suffix in (".doc", ".docx"):
        return _load_docx(path)
    elif suffix == ".txt":
        return _load_txt(path)
    elif suffix == ".md":
        return _load_md(path)
    else:
        raise ValueError(f"不支持的文件格式: {suffix}")


# 图片语法：![](url) —— 图片内容不会进知识库，留着只是噪音
_IMG_PATTERN = re.compile(r"!\[[^\]]*\]\([^)]*\)")
# 行内链接 [文字](url) —— 保留"文字"，丢弃 URL（URL 对语义检索无意义且占长度）
_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^)]*\)")


def _load_md(path: str) -> str:
    """读取 Markdown，去掉图片与链接 URL，保留标题/正文/代码块的语义内容"""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    text = _IMG_PATTERN.sub("", text)
    text = _LINK_PATTERN.sub(r"\1", text)
    return text


def inspect_pdf(path: str) -> dict:
    """体检一份 PDF，返回文字层诊断信息（不抛异常，供排查/预览用）。

    返回: {"pages", "pages_with_text", "chars", "ratio", "is_scan"}
    """
    doc = fitz.open(path)
    try:
        pages = [p.get_text() for p in doc]
    finally:
        doc.close()

    total = len(pages)
    valid = sum(1 for t in pages if len(t.strip()) >= MIN_CHARS_PER_PAGE)
    chars = sum(len(t.strip()) for t in pages)
    ratio = (valid / total) if total else 0.0
    return {
        "pages": total,
        "pages_with_text": valid,
        "chars": chars,
        "ratio": ratio,
        "is_scan": total > 0 and ratio < SCAN_PAGE_RATIO,
    }


def _load_pdf(path: str) -> str:
    doc = fitz.open(path)
    try:
        pages_text = [page.get_text() for page in doc]
    finally:
        doc.close()

    text = "".join(pages_text)
    total = len(pages_text)
    if total == 0:
        return ""

    valid = sum(1 for t in pages_text if len(t.strip()) >= MIN_CHARS_PER_PAGE)
    if valid / total < SCAN_PAGE_RATIO:
        chars = sum(len(t.strip()) for t in pages_text)
        # 扫描版：开了 OCR 就走识别，否则明确报错（绝不静默入库几个字）
        if OCR_ENABLED:
            return _ocr_pdf(path)
        raise ScanPDFError(path, total, valid, chars)
    return text


# ===== OCR：扫描版 PDF 的文字提取 =====
_ocr_engine = None


def _get_ocr_engine():
    """OCR 引擎单例（延迟导入 + 全局缓存）。

    延迟导入：不开 OCR 时连 rapidocr 都不会 import，零代价。
    全局缓存：RapidOCR 每 new 一次都要重新加载 3 个 onnx 模型，
    多页 PDF 逐页 new 会慢到不可用。
    """
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr import RapidOCR
        _ocr_engine = RapidOCR()
    return _ocr_engine


def _pixmap_to_png(doc, xref: int) -> bytes:
    """把 PDF 内嵌图片按【原始分辨率】导出为 PNG 字节。

    为什么不用 page.get_pixmap() 渲染页面：
    扫描件常把小图塞进超大画布——实测某份 PDF 单页 8057x10316pt
    （A4 才 595x842），内嵌图却只有 1080px。渲染等于把 1080px 插值
    放大到 22381 像素，既触发 FzErrorLimit: Overly large image，
    又因模糊反而拉低识别率。直接取内嵌图才是原始清晰度。
    """
    pix = fitz.Pixmap(doc, xref)
    if pix.n - pix.alpha > 3:      # CMYK → RGB，否则导出的 PNG 颜色错乱
        pix = fitz.Pixmap(fitz.csRGB, pix)
    if pix.alpha:                   # 去掉 alpha 通道
        pix = fitz.Pixmap(pix, 0)
    return pix.tobytes("png")


def _ocr_pdf(path: str) -> str:
    """扫描版 PDF → OCR 文字：逐页提取内嵌图片识别，双重过滤后拼接。"""
    engine = _get_ocr_engine()
    doc = fitz.open(path)
    lines = []
    try:
        for page in doc:
            for img in page.get_images(full=True):
                res = engine(_pixmap_to_png(doc, img[0]))
                txts = list(res.txts) if res and getattr(res, "txts", None) else []
                scores = list(res.scores) if res and getattr(res, "scores", None) else []
                for t, s in zip(txts, scores):
                    t = t.strip()
                    # 双重过滤：
                    #   置信度 → 挡"OCR 没看清"的错字
                    #   长度   → 挡"看清了但没意义"的碎片（E-R 图的"一""n""5"）
                    if s >= OCR_MIN_SCORE and len(t) >= OCR_MIN_LINE_LEN:
                        lines.append(t)
    finally:
        doc.close()
    return "\n".join(lines)


def _load_docx(path: str) -> str:
    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def _load_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()
