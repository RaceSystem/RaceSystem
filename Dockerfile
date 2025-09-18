FROM python:3.11-slim

WORKDIR /app

# 安裝 dlib 預編譯 wheel（避免編譯）
RUN pip install --no-cache-dir \
    "dlib==19.24.6" --only-binary :all:

# 安裝其他 Python 套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]
