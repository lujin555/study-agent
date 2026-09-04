"""扫描版 PDF 检测测试

背景：扫描版（影印版）PDF 没有文字层，PyMuPDF 提取出来是空的，
如果不做检测直接入库，会出现「看起来上传成功、实际知识库里什么都没有」的静默失效。
"""
import pymupdf as fitz
import pytest

from rag.loader import load_document, inspect_pdf, ScanPDFError

TEXT = "This is a normal study note with extractable text. "


def _make_text_pdf(path, pages=3, repeats=20):
    """有文字层的正常 PDF"""
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page()
        page.insert_text((72, 100), TEXT * repeats)
    doc.save(str(path))
    doc.close()
    return path


def _make_scan_pdf(path, pages=3):
    """扫描版 PDF：只有图像内容，没有任何文字层"""
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page()
        page.draw_rect(fitz.Rect(50, 50, 400, 400), color=(0.8, 0.8, 0.8), fill=(0.8, 0.8, 0.8))
    doc.save(str(path))
    doc.close()
    return path


def test_text_pdf_loads_normally(tmp_path):
    """正常 PDF：能提取文字，不报扫描版"""
    p = _make_text_pdf(tmp_path / "text.pdf")
    info = inspect_pdf(str(p))
    assert info["pages"] == 3
    assert info["is_scan"] is False
    assert "extractable" in load_document(str(p))


def test_scan_pdf_raises_clearly(tmp_path):
    """扫描版 PDF：应抛出 ScanPDFError，而不是返回空字符串"""
    p = _make_scan_pdf(tmp_path / "scan.pdf")
    info = inspect_pdf(str(p))
    assert info["is_scan"] is True
    assert info["pages_with_text"] == 0

    with pytest.raises(ScanPDFError) as exc:
        load_document(str(p))
    # 错误信息里要让用户看得懂原因和怎么办
    assert "扫描版" in str(exc.value)
    assert "OCR" in str(exc.value)


def test_mixed_pdf_not_mistaken_for_scan(tmp_path):
    """图文混排 PDF：部分页是图，但有足够文字页时不能误杀"""
    doc = fitz.open()
    for i in range(10):
        page = doc.new_page()
        if i < 4:  # 40% 的页有文字
            page.insert_text((72, 100), TEXT * 20)
        else:
            page.draw_rect(fitz.Rect(50, 50, 400, 400), fill=(0.9, 0.9, 0.9))
    p = tmp_path / "mixed.pdf"
    doc.save(str(p))
    doc.close()

    info = inspect_pdf(str(p))
    assert info["is_scan"] is False
    assert load_document(str(p)).strip()


def test_chinese_text_pdf(tmp_path):
    """中文 PDF 同样能被正确识别为有文字层（项目主要场景）"""
    doc = fitz.open()
    page = doc.new_page()
    line = "计算机组成原理：冯诺依曼体系结构的核心是存储程序。"
    for i in range(10):  # insert_text 不会自动换行，需手动分行
        page.insert_text((72, 60 + i * 24), line, fontname="china-s", fontsize=11)
    p = tmp_path / "cn.pdf"
    doc.save(str(p))
    doc.close()

    info = inspect_pdf(str(p))
    assert info["is_scan"] is False
    assert "冯诺依曼" in load_document(str(p))
