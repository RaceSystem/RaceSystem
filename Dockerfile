FROM python:3.11-slim

WORKDIR /app

# 安裝最低限度系統套件（避免編譯）
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 升級 pip
RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt .

# 安裝所有 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

EXPOSE 5000

CMD ["flask", "run"]
