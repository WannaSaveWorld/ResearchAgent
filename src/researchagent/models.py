from pydantic import BaseModel, Field


class Document(BaseModel):
    id: str
    filename: str
    pages: int
    chunks: int


class Chunk(BaseModel):
    id: str
    document_id: str
    filename: str
    page: int | None
    section: str = ''
    text: str
    page_label: str | None = None
    url: str | None = None


class Hit(BaseModel):
    chunk: Chunk
    score: float


class Answer(BaseModel):
    answer: str
    citations: list[Chunk] = Field(default_factory=list)
    evidence_count: int = 0
    refused: bool = False
    warnings: list[str] = Field(default_factory=list)
