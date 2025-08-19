FROM python:3.11-slim

# 添加镜像标签信息
LABEL org.opencontainers.image.title="乐巷酒店数据智能分析系统"
LABEL org.opencontainers.image.description="集成数据管理、可视化分析和AI智能分析功能的酒店运营数据分析系统"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="binbin1213"
LABEL org.opencontainers.image.url="https://github.com/binbin1213/HotelWebBi"
LABEL org.opencontainers.image.source="https://github.com/binbin1213/HotelWebBi"
LABEL org.opencontainers.image.vendor="乐巷酒店"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装依赖，使用官方源或备用镜像源
RUN pip install --no-cache-dir -r requirements.txt || \
    pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ || \
    pip install --no-cache-dir -r requirements.txt -i https://pypi.douban.com/simple/

# 复制应用代码
COPY . .

# 创建日志目录
RUN mkdir -p /app/logs

# 暴露端口
EXPOSE 5004

# 镜像启动时的命令
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5004", "app:app"]
