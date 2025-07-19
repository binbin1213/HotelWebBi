# 酒店分析系统部署指南

## 1. 准备文件

在本地项目中，准备以下文件和目录：

```
local_project/
├── app.py              # 主应用程序文件 
├── ai_service.py       # AI服务模块
├── requirements.txt    # 包含所有依赖
├── Dockerfile          # 已优化，不再复制代码
├── docker-compose.yml  # 已配置使用挂载卷
├── .env                # 环境变量文件
├── static/             # 静态资源目录
└── templates/          # HTML模板目录
```

## 2. 在服务器上创建目录结构

```bash
# 登录到服务器
ssh 用户名@服务器IP

# 创建必要的目录
mkdir -p /home/binbin/hotel_data/logs
mkdir -p /home/binbin/hotel_data/static
mkdir -p /home/binbin/hotel_data/templates
```

## 3. 传输文件到服务器

在本地执行：

```bash
# 传输主要Python文件
scp app.py ai_service.py 用户名@服务器IP:/home/binbin/hotel_data/

# 传输Docker相关文件
scp Dockerfile docker-compose.yml requirements.txt 用户名@服务器IP:/home/binbin/hotel_data/

# 传输环境变量文件
scp .env 用户名@服务器IP:/home/binbin/hotel_data/

# 传输静态资源和模板
scp -r static/* 用户名@服务器IP:/home/binbin/hotel_data/static/
scp -r templates/* 用户名@服务器IP:/home/binbin/hotel_data/templates/
```

## 4. 构建和启动容器

在服务器上执行：

```bash
cd /home/binbin/hotel_data

# 构建镜像
docker-compose build

# 启动容器
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 5. 验证部署

访问 http://服务器IP:5004 检查应用是否正常运行。

## 6. 维护和更新

### 更新代码

只需将修改后的文件传输到服务器上对应的目录，Gunicorn会自动重新加载。

```bash
# 示例：更新app.py
scp app.py 用户名@服务器IP:/home/binbin/hotel_data/
```

### 重启服务

如果需要重启服务：

```bash
docker-compose restart
```

### 完全重建

如果需要完全重建（例如更新依赖）：

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 7. 备份

定期备份数据库和代码：

```bash
# 备份数据库
scp 用户名@服务器IP:/home/binbin/hotel_data/hotel_revenue.db ./backups/hotel_revenue_$(date +%Y%m%d).db

# 备份代码
scp -r 用户名@服务器IP:/home/binbin/hotel_data ./backups/hotel_data_$(date +%Y%m%d)
``` 