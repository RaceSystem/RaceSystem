# 使用官方 Python 3.12 slim 镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 避免 Python 写入 .pyc 文件
ENV PYTHONDONTWRITEBYTECODE=1
# Python 输出不缓存
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    ffmpeg \
    libsm6 \
    libxext6 \
    wget \
    git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 复制 requirements.txt 并安装 Python 依赖
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 复制整个项目
COPY . .

# 暴露 Flask 默认端口
EXPOSE 5000

# 默认执行命令
CMD ["python", "colab_multi_view_race_processor.py"]
