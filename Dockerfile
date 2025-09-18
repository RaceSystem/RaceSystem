FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

# 安裝必要套件，libgl1 替代 libgl1-mesa-glx
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
        ffmpeg \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 更新 pip 並安裝 Python 套件
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案檔案
COPY . .

# 對外暴露 5000 埠口
EXPOSE 5000

# 啟動 app
CMD ["python", "app.py"]
