import hashlib
import re
from io import BytesIO
from pypdf import PdfReader
from researchagent.models import Chunk


def parse_pdf(data: bytes, doc_id: str, filename: str, settings) -> tuple[int, list[Chunk]]:
    try:
        reader = PdfReader(BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise ValueError('Encrypted PDF is not supported')
        count = len(reader.pages)
        if count == 0 or count > settings.max_pdf_pages:
            raise ValueError('PDF page limit exceeded or empty document')
        labels = reader.page_labels
        chunks, section = [], ''
        step = settings.chunk_chars - settings.chunk_overlap
        if step <= 0:
            raise ValueError('chunk_overlap must be smaller than chunk_chars')
        for number, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ''
            text = re.sub(r'[ \t]+', ' ', text).strip()
            for line in text.splitlines():
                heading = line.strip()
                if len(heading) <= 100 and re.match(
                    r'^(?:\d+(?:\.\d+)*\s+\S|Abstract\b|Introduction\b|Methods?\b|Results?\b|Conclusion\b|摘要|引言|方法|结论)',
                    heading, re.I,
                ):
                    section = heading
                    break
            for offset in range(0, len(text), step):
                part = text[offset:offset + settings.chunk_chars].strip()
                if not part:
                    continue
                key = hashlib.sha256(f'{doc_id}:{number}:{offset}'.encode()).hexdigest()[:24]
                chunks.append(Chunk(id=key, document_id=doc_id, filename=filename,
                                    page=number, page_label=labels[number-1], section=section, text=part))
                if offset + settings.chunk_chars >= len(text):
                    break
        if not chunks:
            raise ValueError('No extractable text; scanned PDF requires OCR before upload')
        return count, chunks
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('Invalid or unreadable PDF') from exc
