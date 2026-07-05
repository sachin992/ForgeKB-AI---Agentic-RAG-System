from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ForgeKB AI"
    api_prefix: str = "/api"
    jwt_secret: str = "change_me"
    jwt_algo: str = "HS256"
    access_token_expire_minutes: int = 120

    mysql_user: str = "rag_user"
    mysql_password: str = "rag_password"
    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_db: str = "rag_db"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    uploads_dir: str = "../data/uploads"
    faiss_dir: str = "../data/faiss"
    metadata_store_path: str = "../data/faiss/chunks_manifest.json"
    eval_dataset_path: str = "../eval/eval_dataset.json"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    retrieval_top_k: int = 6
    min_contexts_for_answer: int = 1
    confidence_floor: float = 0.05

    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    redis_url: str = "redis://redis:6379/0"

    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "smart-rag-local"


settings = Settings()


def db_url() -> str:
    return (
        f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}"
        f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_db}"
    )
