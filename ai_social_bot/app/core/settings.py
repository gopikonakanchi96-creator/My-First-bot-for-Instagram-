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
    THREADS_ACCESS_TOKEN: str | None = None
    THREADS_PROFILE_URL: str | None = None
    THREADS_USERNAME: str | None = None
    THREADS_API_VERSION: str = 'v1.0'
    META_GRAPH_API_VERSION: str = 'v23.0'
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = 'gemini-2.5-flash-lite'
    GEMINI_MODEL_FALLBACKS: str = 'gemini-2.0-flash-lite,gemini-2.0-flash'
    OPENAI_MODEL: str = 'gpt-4o'
    OPENAI_MODEL_FALLBACKS: str = 'gpt-4o-mini,gpt-4.1-mini'
    ALLOW_LOCAL_QUOTE_FALLBACK: bool = True
    LOCAL_QUOTE_IMAGE_DIR: str = 'ai_social_bot/local_quote_images'
    LOCAL_QUOTE_IMAGE_CAPTION: str = 'Daily inspiration. Krishna.....'
    DELETE_LOCAL_QUOTE_IMAGE_AFTER_POST: bool = True
    USE_NATURE_BACKGROUNDS: bool = True
    NATURE_BACKGROUND_DIR: str = 'ai_social_bot/assets'
    RECENT_BACKGROUND_MEMORY: int = 12
    POST_TIMES: str = '09:00,11:00,13:00,15:00,17:00'
    POST_TIME_1: str = '09:00'
    POST_TIME_2: str = '17:00'
    SCHEDULER_TIMEZONE: str = 'America/Chicago'
    ENABLE_IN_APP_SCHEDULER: bool = False
    LOGO_PATH: str = 'assets/logo.png'
    DATABASE_URL: str = 'sqlite+aiosqlite:///./ai_social_bot.db'

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        env_ignore_empty = True
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
        return init_settings, env_settings, dotenv_settings, file_secret_settings

settings = Settings()

def get_settings():
    return settings
