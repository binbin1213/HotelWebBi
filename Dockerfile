FROM python:3.11-slim

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装依赖，使用官方源或备用镜像源
RUN pip install --no-cache-dir -r requirements.txt || \
    pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ || \
    pip install --no-cache-dir -r requirements.txt -i https://pypi.douban.com/simple/

# 创建日志目录
RUN mkdir -p /app/logs

# 暴露端口
EXPOSE 5004

# 镜像启动时的命令由docker-compose.yml中的command覆盖
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5004", "app:app", "--reload"] 