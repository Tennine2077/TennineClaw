# ============================================================
# TennineClaw - PDF 文档解析工具集
# ============================================================
# 基于 PyMuPDF (fitz) 实现 PDF 加载、文本提取、搜索等功能
# ============================================================

import os
import json
import traceback
import threading
from collections import OrderedDict
from typing import Any, Dict, Optional

# PyMuPDF 导入
try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


# ============================================================
# PDF 文档缓存（LRU + 线程安全）
# 避免重复打开同一 PDF，自动管理文档生命周期
# ============================================================

class PDFDocumentCache:
    """PDF 文档 LRU 缓存 — 线程安全，自动关闭过期文档"""

    def __init__(self, max_size: int = 5):
        self._cache: OrderedDict[str, fitz.Document] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, path: str) -> Optional[fitz.Document]:
        """获取缓存的文档对象，命中则移至末尾（LRU）"""
        with self._lock:
            if path in self._cache:
                doc = self._cache.pop(path)
                self._cache[path] = doc
                self._hits += 1
                return doc
            self._misses += 1
            return None

    def put(self, path: str, doc: fitz.Document):
        """存入文档，超出容量时淘汰最近最少使用的"""
        with self._lock:
            if path in self._cache:
                # 已存在，移出再插入（更新顺序）
                self._cache.pop(path)
            elif len(self._cache) >= self._max_size:
                # 淘汰最久未使用的
                oldest_path, oldest_doc = self._cache.popitem(last=False)
                try:
                    oldest_doc.close()
                except Exception:
                    pass
            self._cache[path] = doc

    def remove(self, path: str):
        """主动移除缓存中的文档"""
        with self._lock:
            if path in self._cache:
                doc = self._cache.pop(path)
                try:
                    doc.close()
                except Exception:
                    pass

    def clear(self):
        """清空所有缓存并关闭文档"""
        with self._lock:
            for path, doc in self._cache.items():
                try:
                    doc.close()
                except Exception:
                    pass
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                "cache_size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_percent": round(hit_rate, 1)
            }


# 全局 PDF 缓存实例
_pdf_cache = PDFDocumentCache(max_size=5)


def _check_fitz():
    """检查 PyMuPDF 是否可用"""
    if not HAS_FITZ:
        raise ImportError(
            "PyMuPDF 未安装，请执行: pip install PyMuPDF"
        )


def _validate_pdf_path(path: str) -> str:
    """验证 PDF 文件路径是否合法且存在"""
    if not path or not isinstance(path, str):
        raise ValueError("PDF 文件路径不能为空")

    # 规范化路径
    normalized = os.path.normpath(path)

    if not os.path.exists(normalized):
        raise FileNotFoundError(f"PDF 文件不存在: {normalized}")

    if not os.path.isfile(normalized):
        raise ValueError(f"路径不是文件: {normalized}")

    # 检查扩展名
    ext = os.path.splitext(normalized)[1].lower()
    if ext != ".pdf":
        raise ValueError(f"文件不是 PDF 格式（扩展名: {ext}）: {normalized}")

    return normalized


def _open_pdf_safe(path: str) -> fitz.Document:
    """安全打开 PDF 文件（带 LRU 缓存），处理加密等异常"""
    _check_fitz()

    # 先检查缓存
    cached = _pdf_cache.get(path)
    if cached is not None:
        return cached

    # 缓存未命中，打开新文档
    try:
        doc = fitz.open(path)
    except Exception as e:
        error_msg = str(e).lower()
        if "encrypted" in error_msg or "password" in error_msg or "crypt" in error_msg:
            raise PermissionError(f"PDF 文件已加密，无法直接打开: {path}")
        raise RuntimeError(f"打开 PDF 文件失败: {e}")

    # 检查是否需要密码
    if doc.is_encrypted:
        doc.close()
        raise PermissionError(f"PDF 文件已加密，需要密码才能打开: {path}")

    # 存入缓存
    _pdf_cache.put(path, doc)
    return doc


def _extract_toc(doc: fitz.Document) -> list:
    """提取 PDF 目录/书签结构"""
    try:
        toc = doc.get_toc()
        result = []
        for item in toc:
            level, title, page = item
            result.append({
                "level": level,
                "title": title,
                "page": page
            })
        return result
    except Exception:
        return []


def _format_size(size_bytes: int) -> str:
    """将字节数格式化为可读大小"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    else:
        return f"{size_bytes / 1024 / 1024:.1f}MB"


# ============================================================
# 工具函数
# ============================================================

def tool_pdf_load(path: str) -> str:
    """加载 PDF 文件，返回概览信息（页数、元数据、目录结构等）

    Args:
        path: PDF 文件的本地绝对路径

    Returns:
        JSON 字符串，包含页数、元数据、目录、是否有文本层等信息
    """
    try:
        normalized = _validate_pdf_path(path)
        doc = _open_pdf_safe(normalized)

        page_count = doc.page_count
        file_size = os.path.getsize(normalized)

        # 提取元数据
        meta = doc.metadata or {}
        metadata = {
            "title": meta.get("title", "") or "",
            "author": meta.get("author", "") or "",
            "subject": meta.get("subject", "") or "",
            "keywords": meta.get("keywords", "") or "",
            "creator": meta.get("creator", "") or "",
            "producer": meta.get("producer", "") or "",
            "created": meta.get("formatDate(meta.get('creationDate'))", "") or "",
            "modified": meta.get("formatDate(meta.get('modDate'))", "") or "",
        }

        # 尝试获取更友好的日期格式
        try:
            if meta.get("creationDate"):
                raw = meta["creationDate"]
                if raw.startswith("D:"):
                    raw = raw[2:]
                metadata["created"] = raw
        except Exception:
            pass

        try:
            if meta.get("modDate"):
                raw = meta["modDate"]
                if raw.startswith("D:"):
                    raw = raw[2:]
                metadata["modified"] = raw
        except Exception:
            pass

        # 提取目录
        toc = _extract_toc(doc)

        # 检测是否有文本层（扫描前几页）
        has_text = False
        sample_pages = min(page_count, 3)
        text_samples = []
        for i in range(sample_pages):
            try:
                text = doc[i].get_text("text").strip()
                if text:
                    has_text = True
                    text_samples.append(text[:200])
            except Exception:
                text_samples.append("")

        # 获取缓存统计
        cache_stats = _pdf_cache.get_stats()

        result = {
            "success": True,
            "pages": page_count,
            "size_bytes": file_size,
            "size_display": _format_size(file_size),
            "metadata": metadata,
            "toc": toc,
            "has_text": has_text,
            "text_samples": text_samples,
            "path": normalized,
            "cache_stats": cache_stats,
            "hint": (
                "PDF 已加载完成！可使用的后续操作：\n"
                "  • pdf_read_page(path, page_num) — 读取指定页内容\n"
                "  • pdf_search(path, keyword) — 搜索关键词\n"
                "  • pdf_metadata(path) — 查看完整元数据\n"
                "  • pdf_toc(path) — 查看目录结构"
            )
        }

        if not has_text:
            result["warning"] = (
                "该 PDF 可能为扫描版（无文本层），无法直接提取文本。"
                "如需 OCR 识别需要额外工具支持。"
            )

        return json.dumps(result, ensure_ascii=False, indent=2)

    except FileNotFoundError as e:
        return json.dumps({"success": False, "error": str(e), "hint": "请检查文件路径是否正确，可以使用绝对路径如 D:/docs/xxx.pdf"}, ensure_ascii=False)
    except PermissionError as e:
        return json.dumps({"success": False, "error": str(e), "hint": "该 PDF 受密码保护，请提供解密后的文件"}, ensure_ascii=False)
    except ValueError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    except ImportError as e:
        return json.dumps({"success": False, "error": str(e), "hint": "请安装依赖：pip install PyMuPDF"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"加载 PDF 时发生未知错误: {e}",
            "traceback": traceback.format_exc()
        }, ensure_ascii=False)


def tool_pdf_read_page(path: str, page_num: int) -> str:
    """读取 PDF 指定页码的文本内容

    Args:
        path: PDF 文件的本地绝对路径
        page_num: 页码（从 1 开始）

    Returns:
        JSON 字符串，包含页码、总页数、文本内容
    """
    try:
        normalized = _validate_pdf_path(path)
        doc = _open_pdf_safe(normalized)

        total_pages = doc.page_count

        # 页码从 1 开始，转内部 0-based 索引
        if page_num < 1:
            return json.dumps({
                "success": False,
                "error": f"页码必须 >= 1，当前为 {page_num}",
                "total_pages": total_pages,
                "hint": f"有效页码范围: 1 ~ {total_pages}"
            }, ensure_ascii=False)

        if page_num > total_pages:
            return json.dumps({
                "success": False,
                "error": f"页码超出范围，PDF 共 {total_pages} 页，请求第 {page_num} 页",
                "total_pages": total_pages,
                "hint": f"有效页码范围: 1 ~ {total_pages}"
            }, ensure_ascii=False)

        page_index = page_num - 1
        page = doc[page_index]
        text = page.get_text("text").strip()

        # 提取页面中的图片信息（数量）
        image_count = 0
        try:
            images = page.get_images()
            image_count = len(images) if images else 0
        except Exception:
            pass

        if not text:
            return json.dumps({
                "success": True,
                "page": page_num,
                "total_pages": total_pages,
                "text": "",
                "has_text": False,
                "image_count": image_count,
                "warning": "该页无文本内容（可能为纯图片页面）"
            }, ensure_ascii=False)

        # 截断过长的文本（单页超过 10000 字符截断）
        truncated = len(text) > 10000
        if truncated:
            text = text[:10000] + f"\n\n...（内容过长，仅显示前 10000 字符，共 {len(text)} 字符）"

        return json.dumps({
            "success": True,
            "page": page_num,
            "total_pages": total_pages,
            "text": text,
            "has_text": True,
            "image_count": image_count,
            "char_count": len(text),
            "truncated": truncated
        }, ensure_ascii=False)

    except FileNotFoundError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    except PermissionError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    except ValueError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    except ImportError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"读取页面时发生错误: {e}",
            "traceback": traceback.format_exc()
        }, ensure_ascii=False)


def tool_pdf_search(path: str, keyword: str, max_results: int = 10) -> str:
    """在 PDF 中搜索关键词，返回匹配的页码和上下文

    Args:
        path: PDF 文件的本地绝对路径
        keyword: 搜索关键词
        max_results: 最大返回结果数（默认 10，最大 50）

    Returns:
        JSON 字符串，包含匹配总数和结果列表（页码+上下文）
    """
    try:
        if not keyword or not keyword.strip():
            return json.dumps({"success": False, "error": "搜索关键词不能为空"}, ensure_ascii=False)

        keyword = keyword.strip()
        normalized = _validate_pdf_path(path)
        doc = _open_pdf_safe(normalized)

        total_pages = doc.page_count
        results = []
        total_matches = 0

        # 限制最大结果数
        if max_results < 1:
            max_results = 1
        if max_results > 50:
            max_results = 50

        for i in range(total_pages):
            if len(results) >= max_results:
                break

            try:
                page = doc[i]
                text = page.get_text("text")
                if not text:
                    continue

                # 在页面文本中搜索（不区分大小写）
                lower_text = text.lower()
                lower_keyword = keyword.lower()
                count = lower_text.count(lower_keyword)

                if count > 0:
                    total_matches += count

                    # 提取上下文（关键词前后各 100 字符）
                    contexts = []
                    idx = 0
                    while len(contexts) < 3:  # 每页最多提取 3 个上下文片段
                        pos = lower_text.find(lower_keyword, idx)
                        if pos == -1:
                            break

                        contexts.append({
                            "position": pos,
                            "context_before": text[max(0, pos - 80):pos].strip(),
                            "match": text[pos:pos + len(keyword)],
                            "context_after": text[pos + len(keyword):min(len(text), pos + len(keyword) + 80)].strip()
                        })

                        idx = pos + len(keyword)

                    results.append({
                        "page": i + 1,
                        "match_count": count,
                        "contexts": contexts
                    })
            except Exception:
                continue

        return json.dumps({
            "success": True,
            "keyword": keyword,
            "total_matches": total_matches,
            "total_pages_searched": total_pages,
            "pages_with_matches": len(results),
            "results": results,
            "hint": (
                f"共找到 {total_matches} 处匹配，分布在 {len(results)} 页中。\n"
                "可使用 pdf_read_page(path, page_num) 查看具体页面内容"
            )
        }, ensure_ascii=False)

    except FileNotFoundError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    except PermissionError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    except ValueError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    except ImportError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"搜索时发生错误: {e}",
            "traceback": traceback.format_exc()
        }, ensure_ascii=False)


def tool_pdf_metadata(path: str) -> str:
    """提取 PDF 文件的元数据信息

    Args:
        path: PDF 文件的本地绝对路径

    Returns:
        JSON 字符串，包含标题、作者、主题、创建日期等元数据
    """
    try:
        normalized = _validate_pdf_path(path)
        doc = _open_pdf_safe(normalized)

        meta = doc.metadata or {}
        page_count = doc.page_count
        file_size = os.path.getsize(normalized)

        metadata = {
            "title": meta.get("title", "") or "（无标题）",
            "author": meta.get("author", "") or "（未指定作者）",
            "subject": meta.get("subject", "") or "（无主题）",
            "keywords": meta.get("keywords", "") or "（无关键词）",
            "creator": meta.get("creator", "") or "（未记录）",
            "producer": meta.get("producer", "") or "（未记录）",
            "creation_date": meta.get("creationDate", "") or "（未记录）",
            "modification_date": meta.get("modDate", "") or "（未记录）",
        }

        return json.dumps({
            "success": True,
            "file_name": os.path.basename(normalized),
            "file_path": normalized,
            "file_size_display": _format_size(file_size),
            "file_size_bytes": file_size,
            "pages": page_count,
            "metadata": metadata
        }, ensure_ascii=False, indent=2)

    except FileNotFoundError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    except PermissionError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    except ValueError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    except ImportError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"提取元数据时发生错误: {e}"
        }, ensure_ascii=False)


def tool_pdf_toc(path: str) -> str:
    """提取 PDF 的目录/书签结构

    Args:
        path: PDF 文件的本地绝对路径

    Returns:
        JSON 字符串，包含层级化的目录结构
    """
    try:
        normalized = _validate_pdf_path(path)
        doc = _open_pdf_safe(normalized)

        toc = _extract_toc(doc)
        page_count = doc.page_count

        if not toc:
            return json.dumps({
                "success": True,
                "has_toc": False,
                "toc": [],
                "pages": page_count,
                "hint": "该 PDF 无目录/书签结构"
            }, ensure_ascii=False)

        return json.dumps({
            "success": True,
            "has_toc": True,
            "toc": toc,
            "toc_count": len(toc),
            "pages": page_count,
            "hint": f"共 {len(toc)} 个目录项，可使用 pdf_read_page(path, page_num) 跳转到指定页码阅读"
        }, ensure_ascii=False, indent=2)

    except FileNotFoundError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    except PermissionError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    except ValueError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    except ImportError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"提取目录时发生错误: {e}"
        }, ensure_ascii=False)
