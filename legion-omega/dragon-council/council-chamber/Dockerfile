FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn openai redis pydantic --no-cache-dir
COPY democratic_engine.py .
EXPOSE 8090
CMD ["python3", "democratic_engine.py"]
