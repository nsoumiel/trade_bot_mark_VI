FROM python:3.12-slim
WORKDIR /app
COPY --chown=1000:1000 bot /app/bot
RUN mkdir /data && chown 1000:1000 /data
USER 1000:1000
ENV DATA_DIR=/data PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "-m", "bot.app"]
