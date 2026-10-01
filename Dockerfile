# Portability target: `sdk: docker` in README.md plus this file, with hardware changed from a
# dropdown and no rebuild (ARCHITECTURE.md §8.2). The Gradio-SDK deployment does not use it.
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=7860
ENV PYTHONPATH=/app/src
EXPOSE 7860
CMD ["uvicorn", "app_docker:app", "--host", "0.0.0.0", "--port", "7860"]
