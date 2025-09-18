# 使用官方 Python 3.12 slim 映像
FROM python:3.12-slim

# 設置工作目錄
WORKDIR /app

# 拷貝後端與前端程式
COPY . /app

# 升級 pip
RUN pip install --upgrade pip

# 安裝系統依賴（OpenCV 需要一些基礎庫）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Python 套件
RUN pip install --no-cache-dir -r requirements.txt

# 暴露 Flask 默認端口
EXPOSE 5000

# 啟動 Flask
CMD ["python", "app.py"]
