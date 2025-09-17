# 使用官方 Python 3.12 slim 映像
FROM python:3.12-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴（dlib/face-recognition/opencv 編譯需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    wget \
    unzip \
    libopenblas-dev \
    liblapack-dev \
    libboost-all-dev \
    libx11-dev \
    libgtk-3-dev \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements.txt
COPY requirements.txt .

# 安裝 Python 套件
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式
COPY . .

# 設定環境變數
ENV PORT=5000

# 啟動 Flask
CMD ["python", "app.py"]
