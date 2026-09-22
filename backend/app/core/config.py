from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_seconds: float = 45.0
    openrouter_max_retries: int = 3
    kubeconfig_path: str = ""
    kubectl_timeout_seconds: int = 45
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    log_level: str = "INFO"
    insforge_url: str = ""
    insforge_anon_key: str = ""
    app_auth_secret: str = "ai-kubernetes-agent-dev"
    default_user_email: str = "demo@local.dev"
    default_user_password: str = "demo"
    data_dir: str = "data"


settings = Settings()
