# 使用官方 Python 3.12 slim 作為基礎映像
FROM python:3.12-slim

# 設定工作目錄
WORKDIR /app

# 複製當前資料夾的內容到容器
COPY . /app

# 更新 pip 並安裝必要系統依賴
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Python 套件
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 對外暴露端口
EXPOSE 5000

# 啟動 Flask
CMD ["python", "app.py"]
