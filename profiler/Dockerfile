FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /opt/profiler

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN mkdir -p /results

CMD ["python", "-m", "app.main", "run", "all"]
