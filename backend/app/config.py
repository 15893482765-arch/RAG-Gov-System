from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name:str="政务政策RAG系统"
    debug:bool=True
    api_prefix:str="/api"
    database_url:str="mysql+pymysql://root:112419@127.0.0.1:3306/gov_rag?charset=utf8mb4"    # ... 其他配置
    upload_path:Path=Path("data/uploads")
    max_upload_mb:int=20


    model_provider:Literal['ollama','deepseek']="ollama"
    ollama_base_url:str="http://127.0.0.1:11434"
    ollama_model:str="qwen2.5:7b"


    deepseek_api_key:str="sk-ffghmsqsexqmonbouvfhezbhakzfcnifwgntfnzeafaehyog"
    deepseek_base_url:str="https://api.siliconflow.cn/v1"
    deepseek_model:str="deepseek-ai/DeepSeek-V4-Flash"


    milvus_path:Path=Path("data/milvus")
    embedding_model:str="qwen3.7-text-embedding"
    dashscope_api_key:str="sk-ws-H.EHXIYPR.kY1M.MEUCIBCVmczsf029b7xFzMhkgA1AZiRzY2FOiaqb8XtbBfgXAiEAkDehjjapBf32DNaWKjYtKxnNMF83mdXq4LDZxGGWALs"
    model_config = SettingsConfigDict(
        env_file=("../.env",".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )
    reranker_model: str = "BAAI/bge-reranker-base"
    enable_reranker: bool = True
    rerank_top_k: int = 4
    min_evidence_score: float = 0.25


@lru_cache
def get_settings()->Settings:
    return Settings()
