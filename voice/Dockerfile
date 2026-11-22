# ORACLE-Voz internal service: speech-to-text (faster-whisper, CPU int8) and the Keras triage classifier.
# Not published: only the API calls it (http://voice:8001). Heavy libraries stay out of the API image.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TF_CPP_MIN_LOG_LEVEL=2
# espeak-ng: synthetic Spanish speech, used only to MEASURE transcription time (voice/eval/timings.py)
RUN apt-get update && apt-get install -y --no-install-recommends espeak-ng && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
WORKDIR /repo
ENV PYTHONPATH=/repo:/repo/backend
EXPOSE 8001
CMD ["uvicorn", "voice.triage.service:app", "--host", "0.0.0.0", "--port", "8001"]
