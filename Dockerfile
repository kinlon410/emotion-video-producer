FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装额外依赖
RUN pip install --no-cache-dir \
    celery[redis] \
    redis \
    flask_sock \
    simple-websocket \
    aiohttp \
    pydantic

# 复制代码
COPY . .

# 创建共享目录
RUN mkdir -p /tmp/emotion_video_shared

# 默认命令
CMD ["python", "web_api.py"]