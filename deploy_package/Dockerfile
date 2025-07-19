FROM python:3.11-slim

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 使用国内镜像源安装依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 创建日志目录
RUN mkdir -p /app/logs

# 暴露端口
EXPOSE 5004

# 镜像启动时的命令由docker-compose.yml中的command覆盖
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5004", "app:app", "--reload"] 