FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev gcc pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        "fastapi[standard]>=0.115.11" \
        "sqlalchemy>=2.0.38" \
        "sqlmodel>=0.0.24" \
        "pymysql>=1.1.0" \
        "python-jose[cryptography]>=3.3.0" \
        "passlib[bcrypt]>=1.7.4" \
        "bcrypt==4.0.1" \
        "cryptography>=42.0.0" \
        "httpx>=0.27.0" \
        "python-multipart>=0.0.9" \
        "fastmcp>=2.0.0" \
        "jinja2>=3.1.0" \
        "uvicorn>=0.30.0"

COPY . .

RUN mkdir -p /app/keys
VOLUME ["/app/keys"]

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
