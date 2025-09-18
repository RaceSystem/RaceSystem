# 基礎映像
FROM python:3.11-slim

# 設定環境變數
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 建立專案資料夾
WORKDIR /app

# 安裝系統依賴（dlib wheel 也可能需要的庫）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    pkg-config \
    git \
    wget \
    curl \
    ca-certificates \
    libstdc++6 \
    libopenblas-dev \
    liblapack-dev \
    libboost-all-dev \
    ffmpeg \
    libjpeg-dev \
    zlib1g-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 複製專案檔案
COPY . /app

# 升級 pip
RUN pip install --upgrade pip

# 安裝 Python 套件
RUN pip install --no-cache-dir -r requirements.txt

# 建立 swap（2GB）
RUN fallocate -l 2G /swapfile && \
    chmod 600 /swapfile && \
    mkswap /swapfile && \
    swapon /swapfile

# 開放 5000 port
EXPOSE 5000

# 啟動 Flask
CMD ["python", "app.py"]
