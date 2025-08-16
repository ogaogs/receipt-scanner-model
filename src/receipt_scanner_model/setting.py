from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
    )
    bucket_name: str = "receipt-scanner-v1"
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_default_region: str
    openai_api_key: str


# NOTE: 自動的に.envから環境変数を読み込むため、Settingの引数は必要ない
setting = Settings()  # type: ignore
