FROM python:3.12-slim
WORKDIR /app
COPY ./ai_social_bot /app/ai_social_bot
COPY ./ai_social_bot/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
EXPOSE 8000
CMD ["uvicorn", "ai_social_bot.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
