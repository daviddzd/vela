# SIRAG-D runs OFFLINE, faster than real time, and only writes CSV files to simulation/results/.
# It has no database driver on purpose: it reads the seed CSVs and can never modify the operation DB.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /repo
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
# the repo is mounted at /repo; the dispatcher is imported from backend/app/services
ENV PYTHONPATH=/repo:/repo/backend
CMD ["python", "-m", "simulation.experiments.run"]
