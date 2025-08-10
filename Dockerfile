FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y \
        stockfish \
        make && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN dbt deps --project-dir /app/dbt

WORKDIR /app/dbt
CMD ["python", "run_all.py"]