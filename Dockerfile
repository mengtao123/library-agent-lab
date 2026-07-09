FROM python:3.10-slim

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制整个项目
COPY . .

# 暴露端口
EXPOSE 8000 8001 8002 8003

# 启动服务
CMD ["python", "server.py"]