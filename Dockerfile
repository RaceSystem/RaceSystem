FROM python:3.12-slim

WORKDIR /app

# 安裝必要依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements.txt
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案
COPY . .

EXPOSE 5000
CMD ["python", "colab_multi_view_race_processor.py"]
