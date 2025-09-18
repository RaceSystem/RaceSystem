# 使用 Python 3.11 slim
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴（編譯 dlib / opencv / ffmpeg 所需）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    pkg-config \
    git \
    wget \
    curl \
    ca-certificates \
    gcc \
    g++ \
    libstdc++6 \
    libopenblas-dev \
    liblapack-dev \
    libboost-all-dev \
    libxrender1 libxext6 libx11-6 libxcb1 \
    libglib2.0-0 \
    libsm6 libice6 libxrender-dev \
    ffmpeg \
    libjpeg-dev \
    zlib1g-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 複製 requirements.txt
COPY requirements.txt .

# 安裝 Python 套件
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案程式
COPY . .

# 設定 Flask 環境變數
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# 開放 port
EXPOSE 5000

# 啟動 Flask
CMD ["flask", "run"]
