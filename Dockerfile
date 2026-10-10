FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libgomp1 \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Set cache dir explicitly
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface
ENV HF_HOME=/app/.cache/huggingface

# Pre-download models during build
RUN python -c "\
import os; \
os.makedirs('/app/.cache/huggingface', exist_ok=True); \
from transformers import AutoModelForSequenceClassification, AutoTokenizer; \
AutoTokenizer.from_pretrained('cardiffnlp/twitter-roberta-base-sentiment-latest', cache_dir='/app/.cache/huggingface'); \
AutoModelForSequenceClassification.from_pretrained('cardiffnlp/twitter-roberta-base-sentiment-latest', cache_dir='/app/.cache/huggingface'); \
AutoTokenizer.from_pretrained('cross-encoder/nli-distilroberta-base', cache_dir='/app/.cache/huggingface'); \
AutoModelForSequenceClassification.from_pretrained('cross-encoder/nli-distilroberta-base', cache_dir='/app/.cache/huggingface'); \
print('Models cached successfully!')"

COPY . .

EXPOSE 7860

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "7860"]
