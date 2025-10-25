# 使用官方Python镜像替代GitHub Container Registry
FROM python:3.10-slim-bookworm

# 安装uv包管理器
RUN pip install -i https://mirrors.aliyun.com/pypi/simple uv

WORKDIR /app

RUN mkdir -p /app/data /app/logs

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN echo 'deb http://mirrors.aliyun.com/debian/ bookworm main' > /etc/apt/sources.list && \
    echo 'deb-src http://mirrors.aliyun.com/debian/ bookworm main' >> /etc/apt/sources.list && \
    echo 'deb http://mirrors.aliyun.com/debian/ bookworm-updates main' >> /etc/apt/sources.list && \
    echo 'deb-src http://mirrors.aliyun.com/debian/ bookworm-updates main' >> /etc/apt/sources.list && \
    echo 'deb http://mirrors.aliyun.com/debian-security bookworm-security main' >> /etc/apt/sources.list && \
    echo 'deb-src http://mirrors.aliyun.com/debian-security bookworm-security main' >> /etc/apt/sources.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    wkhtmltopdf \
    xvfb \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    fonts-liberation \
    pandoc \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 启动Xvfb虚拟显示器
RUN echo '#!/bin/bash\n\
# Remove stale lock file if it exists\n\
rm -f /tmp/.X99-lock\n\
# Kill any existing Xvfb processes on display :99\n\
pkill -f "Xvfb :99" || true\n\
# Start Xvfb in the background\n\
Xvfb :99 -screen 0 1024x768x24 -ac +extension GLX &\n\
# Wait for Xvfb to start\n\
sleep 2\n\
export DISPLAY=:99\n\
exec "$@"' > /usr/local/bin/start-xvfb.sh \
    && chmod +x /usr/local/bin/start-xvfb.sh

COPY requirements.txt .

#多源轮询安装依赖
RUN for src in \
        https://mirrors.aliyun.com/pypi/simple \
        https://pypi.tuna.tsinghua.edu.cn/simple \
        https://pypi.doubanio.com/simple \
        https://pypi.org/simple; do \
      echo "Try installing from $src"; \
      if pip install --no-cache-dir -r requirements.txt -i $src; then \
        echo "Successfully installed from $src"; \
        break; \
      else \
        echo "Failed at $src, try next"; \
      fi; \
    done && \
    python -c "import streamlit; print('Streamlit version:', streamlit.__version__)"

# 复制日志配置文件
COPY config/ ./config/

COPY . .

EXPOSE 8501

CMD ["python", "-m", "streamlit", "run", "web/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
