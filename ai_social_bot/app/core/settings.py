from pydantic_settings import BaseSettings
from pydantic_settings import PydanticBaseSettingsSource

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    META_PAGE_ACCESS_TOKEN: str
    FACEBOOK_PAGE_ID: str
    FACEBOOK_PAGE_URL: str | None = None
    FACEBOOK_PAGE_NAME: str | None = None
    INSTAGRAM_PROFILE_URL: str | None = None
    INSTAGRAM_USERNAME: str | None = None
    META_GRAPH_API_VERSION: str = 'v23.0'
    OPENAI_MODEL: str = 'gpt-4o'
    OPENAI_MODEL_FALLBACKS: str = 'gpt-4o-mini,gpt-4.1-mini'
    ALLOW_LOCAL_QUOTE_FALLBACK: bool = True
    USE_NATURE_BACKGROUNDS: bool = True
    NATURE_BACKGROUND_DIR: str = 'ai_social_bot/assets'
    POST_TIMES: str = '09:00,11:00,13:00,15:00,17:00'
    POST_TIME_1: str = '09:00'
    POST_TIME_2: str = '17:00'
    SCHEDULER_TIMEZONE: str = 'America/Chicago'
    LOGO_PATH: str = 'assets/logo.png'
    DATABASE_URL: str = 'sqlite+aiosqlite:///./ai_social_bot.db'

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore'

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return init_settings, dotenv_settings, env_settings, file_secret_settings

settings = Settings()

def get_settings():
    return settings
