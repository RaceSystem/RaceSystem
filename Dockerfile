# 使用 Python 3.10，保證套件兼容性
FROM python:3.10-slim

# 設定工作目錄
WORKDIR /app

# 複製需求檔
COPY requirements.txt .

# 安裝系統依賴（opencv headless 需要）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
        ffmpeg \
        && rm -rf /var/lib/apt/lists/*

# 安裝 Python 套件
RUN pip install --no-cache-dir -r requirements.txt

# 複製你的後端與前端程式
COPY . .

# 暴露 Flask 默認端口
EXPOSE 5000

# 啟動 Flask
CMD ["python", "app.py"]
