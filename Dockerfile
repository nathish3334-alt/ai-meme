FROM python:3.10-slim

WORKDIR /app

# Install system dependencies if any compiling is needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install dependencies (this will use precompiled wheels for python 3.10)
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose the port Render expects
EXPOSE 10000

ENV PORT=10000
ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "--workers", "1", "--timeout", "120", "--bind", "0.0.0.0:10000", "web_app:app"]
