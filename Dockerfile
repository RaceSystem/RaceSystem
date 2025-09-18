# 使用 Python 3.12 slim 映像
FROM python:3.12-slim

# 設定工作目錄
WORKDIR /app

# 安裝必要系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
        ffmpeg \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements.txt
COPY requirements.txt .

# 升級 pip、setuptools、wheel
RUN pip install --upgrade pip setuptools wheel

# 安裝 Python 套件
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案檔案
COPY . .

# 開放 5000 port
EXPOSE 5000

# 啟動 Flask 應用
CMD ["python", "app.py"]
