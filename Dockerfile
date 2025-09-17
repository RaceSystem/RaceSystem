# 使用 Python 3.11 官方 slim 版
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴（face-recognition 需要 cmake、boost 等）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    libboost-python-dev \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements.txt 並安裝 Python 套件
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼
COPY . .

# 暴露 port
EXPOSE 5000

# 啟動 Flask
CMD ["python", "app.py"]
