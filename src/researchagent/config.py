from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='RA_', env_file='.env', extra='ignore')
    data_dir: Path = Path('data')
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, ge=1)
    max_pdf_pages: int = Field(default=500, ge=1)
    chunk_chars: int = Field(default=1400, ge=200)
    chunk_overlap: int = Field(default=150, ge=0)
    embedding_backend: str = 'api'
    embedding_model: str = 'text-embedding-3-small'
    embedding_base_url: str = 'https://api.openai.com/v1'
    embedding_api_key: SecretStr = SecretStr('')
    chat_model: str = 'openai/gpt-4o-mini'
    chat_base_url: str = 'https://api.openai.com/v1'
    chat_api_key: SecretStr = SecretStr('')
    top_k: int = Field(default=6, ge=1, le=20)
    timeout_seconds: float = Field(default=90, gt=0, le=600)
    mcp_url: str = ''
    mcp_tool: str = 'search_papers'
    max_tool_calls: int = Field(default=1, ge=0, le=3)
    graph_recursion_limit: int = Field(default=12, ge=6, le=30)
