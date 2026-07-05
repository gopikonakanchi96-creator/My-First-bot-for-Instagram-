# AI Facebook Quote Bot

Generates quote images and publishes them to a Facebook Page and the connected Instagram business account.

## Required environment

Copy `.env.example` to `.env` and set:

- `OPENAI_API_KEY`
- `META_PAGE_ACCESS_TOKEN`
- `FACEBOOK_PAGE_ID`
- `META_GRAPH_API_VERSION` defaults to `v23.0`
- `OPENAI_MODEL_FALLBACKS` can list backup models separated by commas
- `ALLOW_LOCAL_QUOTE_FALLBACK=true` creates a local quote if all OpenAI models fail
- `USE_NATURE_BACKGROUNDS=true` uses saved nature image backgrounds for quote posts

The app schedules two daily Facebook Page photo posts using `POST_TIME_1` and `POST_TIME_2`.
