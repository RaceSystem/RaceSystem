# 基底 image（輕量但可編譯 dlib）
FROM python:3.11-slim

# 設定非互動模式
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安裝系統套件（編譯 dlib / opencv / ffmpeg 所需）
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
    libatlas-base-dev \
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

# 建立工作目錄
WORKDIR /app

# 複製 requirements
COPY requirements.txt /app/requirements.txt

# 先安裝 wheel 與 pip 最新版，再安裝 requirements
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt

# 複製應用程式程式碼（請確保 app.py 與 static 目錄在同層）
COPY . /app

# 建立可寫入的臨時資料夾（與你的程式一致）
RUN mkdir -p /tmp/final_project/uploads /tmp/final_project/results /tmp/final_project/static

# 對外埠（Render 預設使用 PORT env）
EXPOSE 5000

# 使用 gunicorn 啟動（Render 會傳入 PORT env var）
CMD ["sh", "-c", "exec gunicorn app:app --bind 0.0.0.0:${PORT:-5000} --workers 3 --threads 2 --timeout 120"]
