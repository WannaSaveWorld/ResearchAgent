from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

import pytest
from reportlab.pdfgen.canvas import Canvas
from pypdf import PdfWriter

from researchagent.config import Settings
from researchagent.store import Store


def pdf_bytes(*pages):
    stream = BytesIO()
    canvas = Canvas(stream)
    for text in pages:
        canvas.drawString(40, 750, text)
        canvas.showPage()
    canvas.save()
    return stream.getvalue()


@pytest.fixture
def store(tmp_path):
    return Store(Settings(data_dir=tmp_path, chunk_chars=300, chunk_overlap=40))


def test_pages_and_restart_and_dedup(store):
    data = pdf_bytes('1 Introduction: visible light fusion.', '2 Methods: thermal depth fusion.')
    doc = store.add_pdf(data, '../../paper.pdf')
    assert doc.filename == 'paper.pdf'
    assert doc.pages == 2
    chunks = store.chunks()
    assert {c.page for c in chunks} == {1, 2}
    assert len({c.id for c in chunks}) == len(chunks)
    assert store.add_pdf(data, 'renamed.pdf').id == doc.id
    again = Store(store.settings)
    assert len(again.documents()) == 1
    assert [c.id for c in again.chunks()] == [c.id for c in chunks]
    assert again.document_path(doc.id).read_bytes() == data


def test_same_name_different_content(store):
    a = store.add_pdf(pdf_bytes('First paper with enough readable words.'), 'a.pdf')
    b = store.add_pdf(pdf_bytes('Second paper with different readable words.'), 'a.pdf')
    assert a.id != b.id
    assert len(store.documents()) == 2


def test_invalid_empty_and_limits(store):
    with pytest.raises(ValueError, match='PDF'):
        store.add_pdf(b'not pdf', 'a.pdf')
    stream = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(stream)
    with pytest.raises(ValueError, match='OCR'):
        store.add_pdf(stream.getvalue(), 'scan.pdf')
    store.settings.max_upload_bytes = 10
    with pytest.raises(ValueError, match='size'):
        store.add_pdf(pdf_bytes('data'), 'a.pdf')


def test_concurrent_duplicate_upload(store):
    data = pdf_bytes('Concurrent document used for duplicate upload testing.')
    with ThreadPoolExecutor(max_workers=3) as pool:
        ids = list(pool.map(lambda _: store.add_pdf(data, 'x.pdf').id, range(3)))
    assert len(set(ids)) == 1
    assert len(store.documents()) == 1


def test_sessions_are_isolated_and_persisted(store):
    a, b = store.create_session(), store.create_session()
    store.add_message(a, 'user', 'alpha')
    assert store.messages(b) == []
    assert Store(store.settings).messages(a)[0]['content'] == 'alpha'
    with pytest.raises(KeyError):
        store.messages('missing')
