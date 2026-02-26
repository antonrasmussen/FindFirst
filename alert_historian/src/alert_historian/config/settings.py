from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
  model_config = SettingsConfigDict(
      env_file=".env",
      env_file_encoding="utf-8",
      extra="ignore",
  )

  state_db: Path = Field(default=Path("./state/alert_historian.db"), alias="ALERT_HISTORIAN_STATE_DB")
  artifacts_dir: Path = Field(default=Path("./artifacts"), alias="ALERT_HISTORIAN_ARTIFACTS_DIR")
  reports_dir: Path = Field(default=Path("./reports/daily"), alias="ALERT_HISTORIAN_REPORTS_DIR")

  input_mode: str = Field(default="json", alias="ALERT_HISTORIAN_INPUT_MODE")
  json_input: Path = Field(default=Path("./sample/alerts.json"), alias="ALERT_HISTORIAN_JSON_INPUT")

  imap_host: str = Field(default="imap.gmail.com", alias="ALERT_HISTORIAN_IMAP_HOST")
  imap_port: int = Field(default=993, alias="ALERT_HISTORIAN_IMAP_PORT")
  imap_username: str = Field(default="", alias="ALERT_HISTORIAN_IMAP_USERNAME")
  imap_password: str = Field(default="", alias="ALERT_HISTORIAN_IMAP_PASSWORD")
  imap_folder: str = Field(default="INBOX", alias="ALERT_HISTORIAN_IMAP_FOLDER")
  imap_since_uid: int = Field(default=0, alias="ALERT_HISTORIAN_IMAP_SINCE_UID")

  alert_list_id: str = Field(default="alerts.google.com", alias="ALERT_HISTORIAN_ALERT_LIST_ID")
  alert_sender: str = Field(default="googlealerts-noreply@google.com", alias="ALERT_HISTORIAN_ALERT_SENDER")

  findfirst_base_url: str = Field(default="http://localhost:9000", alias="ALERT_HISTORIAN_FINDFIRST_BASE_URL")
  findfirst_username: str = Field(default="jsmith", alias="ALERT_HISTORIAN_FINDFIRST_USERNAME")
  findfirst_password: str = Field(default="test", alias="ALERT_HISTORIAN_FINDFIRST_PASSWORD")

  sync_batch_size: int = Field(default=100, alias="ALERT_HISTORIAN_SYNC_BATCH_SIZE")
  use_domain_tags: bool = Field(default=True, alias="ALERT_HISTORIAN_USE_DOMAIN_TAGS")

  chroma_path: Path = Field(default=Path("./artifacts/chroma"), alias="ALERT_HISTORIAN_CHROMA_PATH")
  embedding_model: str = Field(default="text-embedding-3-small", alias="ALERT_HISTORIAN_EMBEDDING_MODEL")
  openai_api_key: str = Field(default="", alias="ALERT_HISTORIAN_OPENAI_API_KEY")
  llm_model: str = Field(default="gpt-4o-mini", alias="ALERT_HISTORIAN_LLM_MODEL")
  chronicle_path: Path = Field(default=Path("./artifacts/chronicle.md"), alias="ALERT_HISTORIAN_CHRONICLE_PATH")


@lru_cache
def get_settings() -> Settings:
  return Settings()
