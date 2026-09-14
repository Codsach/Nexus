from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Nexus"
    app_version: str = "0.1.0"
    debug: bool = True

    database_url: str = "sqlite+aiosqlite:///./nexus.db"

    llm_provider: str = "mock"
    orchestration_provider: str = "mock"

    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-max"

    enterpro_api_key: str = ""
    enterpro_base_url: str = ""

    # Vector store — using chromadb with in-memory fallback if hnswlib unavailable
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection: str = "nexus_knowledge"
    use_simple_retrieval: bool = False  # fallback if chromadb unavailable

    demo_customer_id: str = "C001"
    cors_origins: str = "http://localhost:5173,http://localhost:3000,*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
