# 使用 Python 3.12-slim，滿足所有套件要求
FROM python:3.12-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴（替換過時的 libgl1-mesa-glx）
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
        ffmpeg \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements.txt 並安裝 Python 套件
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案文件
COPY . .

# 開放 5000 端口
EXPOSE 5000

# 啟動 Flask
CMD ["python", "app.py"]
