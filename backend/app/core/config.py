import os


class Settings:
    POSTGRES_HOST: str = os.environ.get("POSTGRES_HOST", "localhost")
    POSTGRES_DB: str = os.environ.get("POSTGRES_DB", "geoassets")
    POSTGRES_USER: str = os.environ.get("POSTGRES_USER", "geoassets")
    POSTGRES_PASSWORD: str = os.environ.get("POSTGRES_PASSWORD", "geoassets")
    POSTGRES_PORT: int = int(os.environ.get("POSTGRES_PORT", "5432"))

    REDIS_HOST: str = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.environ.get("REDIS_PORT", "6379"))
    REDIS_TTL_SECONDS: int = int(os.environ.get("REDIS_TTL_SECONDS", "86400"))

    GOOGLE_MAPS_API_KEY: str = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    MAPS_MAX_QUERY_BUDGET: int = int(os.environ.get("MAPS_MAX_QUERY_BUDGET", "50"))
    MAPS_MAX_RESULTS_PER_QUERY: int = int(os.environ.get("MAPS_MAX_RESULTS_PER_QUERY", "20"))
    MAPS_KEYWORDS_PER_CATEGORY: int = int(os.environ.get("MAPS_KEYWORDS_PER_CATEGORY", "8"))
    MAPS_MAX_CONCURRENT_REQUESTS: int = int(os.environ.get("MAPS_MAX_CONCURRENT_REQUESTS", "10"))

    LITELLM_MODEL: str = os.environ.get("LITELLM_MODEL", "bedrock/openai.gpt-oss-120b-1:0")
    LITELLM_FALLBACK_MODEL: str = os.environ.get("LITELLM_FALLBACK_MODEL", "")
    AGENT_LITELLM_MODEL: str = os.environ.get("AGENT_LITELLM_MODEL", LITELLM_MODEL)
    AGENT_LITELLM_FALLBACK_MODEL: str = os.environ.get("AGENT_LITELLM_FALLBACK_MODEL", LITELLM_FALLBACK_MODEL)
    PIPELINE_LITELLM_MODEL: str = os.environ.get("PIPELINE_LITELLM_MODEL", LITELLM_MODEL)
    PIPELINE_LITELLM_FALLBACK_MODEL: str = os.environ.get("PIPELINE_LITELLM_FALLBACK_MODEL", LITELLM_FALLBACK_MODEL)
    LITELLM_MAX_WORKERS: int = int(os.environ.get("LITELLM_MAX_WORKERS", "5"))
    LITELLM_TIMEOUT: int = int(os.environ.get("LITELLM_TIMEOUT", "30"))

    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
    AWS_REGION_NAME: str = os.environ.get("AWS_REGION_NAME", "eu-west-1")

    AGENT_SESSION_DIR: str = os.environ.get("AGENT_SESSION_DIR", "/tmp/agent_sessions")
    AGENT_MAX_DURATION_SECONDS: int = int(os.environ.get("AGENT_MAX_DURATION_SECONDS", "120"))
    AGENT_MAX_FILES: int = int(os.environ.get("AGENT_MAX_FILES", "5"))
    AGENT_MAX_ITERATIONS: int = int(os.environ.get("AGENT_MAX_ITERATIONS", "15"))

    CONFIDENCE_THRESHOLD_HIGH: float = float(os.environ.get("CONFIDENCE_THRESHOLD_HIGH", "0.65"))
    CONFIDENCE_THRESHOLD_MEDIUM: float = float(os.environ.get("CONFIDENCE_THRESHOLD_MEDIUM", "0.35"))
    UPLOAD_MAX_SIZE_MB: int = int(os.environ.get("UPLOAD_MAX_SIZE_MB", "25"))
    OMP_NUM_THREADS: int = int(os.environ.get("OMP_NUM_THREADS", "4"))
    DOCLING_NUM_THREADS: int = int(os.environ.get("DOCLING_NUM_THREADS", "4"))
    DOCLING_PDF_OCR: bool = os.environ.get("DOCLING_PDF_OCR", "false").lower() in {"1", "true", "yes"}
    DOC_EXTRACTION_MAX_CONCURRENCY: int = int(os.environ.get("DOC_EXTRACTION_MAX_CONCURRENCY", "8"))
    DOC_GEOCODE_MAX_CONCURRENCY: int = int(os.environ.get("DOC_GEOCODE_MAX_CONCURRENCY", "8"))

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def database_url_sync(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
