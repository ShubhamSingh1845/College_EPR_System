from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://127.0.0.1:27017"
    mongodb_database: str = "college_erp"
    jwt_secret: str = ""
    jwt_expire_minutes: int = 60
    backend_port: int = 8001
    frontend_origin: str = "http://127.0.0.1:5173,http://localhost:5173"
    erp_seed_admin_email: str = "admin@example.edu"
    erp_seed_admin_password: str = ""
    payment_mode: str = "test"
    payment_gateway_key: str = ""
    payment_gateway_secret: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
