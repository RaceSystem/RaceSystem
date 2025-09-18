# 基礎映像
FROM python:3.12-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴（避免 dlib 編譯問題）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements.txt
COPY requirements.txt .

# 升級 pip 並安裝依賴
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案文件
COPY . .

# 暴露端口
EXPOSE 5000

# 啟動 Flask
CMD ["python", "app.py"]
