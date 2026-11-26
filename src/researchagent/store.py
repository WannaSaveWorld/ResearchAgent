import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from uuid import uuid4
from researchagent.ingest import parse_pdf
from researchagent.models import Chunk, Document


class Store:
    def __init__(self, settings):
        self.settings = settings
        self.root = settings.data_dir.resolve()
        (self.root/'pdfs').mkdir(parents=True, exist_ok=True)
        self.db = self.root/'researchagent.sqlite3'
        self.lock = threading.RLock()
        with self.connect() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY, document_id TEXT, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT, role TEXT, content TEXT);
            ''')

    def connect(self):
        return sqlite3.connect(self.db, timeout=30)

    def add_pdf(self, data: bytes, filename: str) -> Document:
        if len(data) > self.settings.max_upload_bytes:
            raise ValueError('PDF size limit exceeded')
        if not data.startswith(b'%PDF-'):
            raise ValueError('Expected a PDF file')
        name = Path(filename.replace('\\', '/')).name[:200] or 'paper.pdf'
        doc_id = hashlib.sha256(data).hexdigest()
        with self.lock:
            try:
                return self.get_document(doc_id)
            except KeyError:
                pass
            pages, chunks = parse_pdf(data, doc_id, name, self.settings)
            doc = Document(id=doc_id, filename=name, pages=pages, chunks=len(chunks))
            target = self.root/'pdfs'/f'{doc_id}.pdf'
            temporary = target.with_suffix('.tmp')
            temporary.write_bytes(data)
            temporary.replace(target)
            with self.connect() as conn:
                conn.execute('INSERT OR IGNORE INTO documents VALUES (?,?)', (doc_id, doc.model_dump_json()))
                conn.executemany('INSERT OR IGNORE INTO chunks VALUES (?,?,?)',
                                 [(c.id, doc_id, c.model_dump_json()) for c in chunks])
            return doc

    def get_document(self, doc_id: str) -> Document:
        with self.connect() as conn:
            row = conn.execute('SELECT body FROM documents WHERE id=?', (doc_id,)).fetchone()
        if row is None:
            raise KeyError('Document not found')
        return Document.model_validate_json(row[0])

    def document_path(self, doc_id: str) -> Path:
        self.get_document(doc_id)
        return self.root/'pdfs'/f'{doc_id}.pdf'

    def documents(self) -> list[Document]:
        with self.connect() as conn:
            return [Document.model_validate_json(r[0]) for r in
                    conn.execute('SELECT body FROM documents ORDER BY rowid')]

    def chunks(self, document_ids=None) -> list[Chunk]:
        with self.connect() as conn:
            rows = conn.execute('SELECT body FROM chunks ORDER BY rowid').fetchall()
        items = [Chunk.model_validate_json(r[0]) for r in rows]
        return items if document_ids is None else [c for c in items if c.document_id in document_ids]

    def create_session(self) -> str:
        key = uuid4().hex
        with self.connect() as conn:
            conn.execute('INSERT INTO sessions VALUES (?)', (key,))
        return key

    def messages(self, session_id: str) -> list[dict]:
        with self.connect() as conn:
            if not conn.execute('SELECT 1 FROM sessions WHERE id=?', (session_id,)).fetchone():
                raise KeyError('Session not found')
            return [dict(role=r[0], content=r[1]) for r in conn.execute(
                'SELECT role,content FROM messages WHERE session_id=? ORDER BY id', (session_id,))]

    def add_message(self, session_id, role, content):
        self.messages(session_id)
        with self.connect() as conn:
            conn.execute('INSERT INTO messages(session_id,role,content) VALUES (?,?,?)',
                         (session_id, role, content if isinstance(content, str) else json.dumps(content)))
