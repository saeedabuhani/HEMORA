from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./hemora.db"
    jwt_secret: str = "development-only-secret-change-before-production"
    national_id_encryption_key: str = ""
    national_id_hmac_key: str = "development-hmac-key"
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Keep the production default strict; relax only for automated end-to-end runs.
    login_rate_limit: str = "10/minute"
    # DEMO ONLY. Every account, including patient logins created through the
    # UI, is given this password so the system can be demonstrated without
    # handing out individual credentials. A real deployment must remove this
    # and issue a unique one-time password per account.
    default_user_password: str = "Hemora123!"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
