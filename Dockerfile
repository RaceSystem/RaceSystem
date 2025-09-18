# 使用輕量 Python 3.11
FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴（ffmpeg, opencv, 基本編譯庫）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 libxext6 libxrender-dev \
    libjpeg-dev \
    zlib1g-dev \
    build-essential \
    git \
    wget \
    curl \
    ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 複製專案
COPY . /app

# 升級 pip 並安裝 Python 套件
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 開放 5000 端口
EXPOSE 5000

# 啟動 Flask
CMD ["python", "app.py"]
