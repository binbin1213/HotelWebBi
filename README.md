# 酒店数据智能分析系统 - Docker部署指南

这个项目是酒店的数据智能分析系统，集成了数据管理、可视化分析和AI智能分析功能。本指南将帮助您使用Docker部署该系统。

## 系统要求

- Docker
- Docker Compose

## 快速部署

### 方式一：使用 Docker Hub 镜像（推荐）

```bash
# 1. 克隆代码库
git clone https://github.com/binbin1213/HotelWebBi.git
cd HotelWebBi

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的配置

# 3. 使用 Docker Hub 镜像启动
docker-compose -f docker-compose.dockerhub.yml up -d
```

### 方式二：使用 GitHub Container Registry

```bash
# 1. 克隆代码库
git clone https://github.com/binbin1213/HotelWebBi.git
cd HotelWebBi

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的配置

# 3. 使用 GHCR 镜像启动
docker-compose -f docker-compose.github.yml up -d
```

### 方式三：本地构建

```bash
# 1. 克隆代码库
git clone https://github.com/binbin1213/HotelWebBi.git
cd HotelWebBi

# 2. 构建并启动Docker容器
docker-compose up -d
```

这将构建Docker镜像并在后台启动容器。

### 3. 访问系统

系统启动后，可以通过浏览器访问：

```
http://localhost:5004
```

## 数据持久化

系统使用SQLite数据库存储数据。数据库文件`hotel_revenue.db`被挂载为卷，因此数据会在容器重启后保留。

## 停止系统

要停止系统，请运行：

```bash
docker-compose down
```

## 查看日志

要查看系统日志，请运行：

```bash
docker-compose logs -f
```

## 重新构建

如果您对代码进行了更改，需要重新构建镜像：

```bash
docker-compose build
docker-compose up -d
```

## 系统功能

- 数据导入：支持Excel数据导入
- 数据可视化：多种图表展示酒店运营数据
- AI分析：集成DeepSeek AI进行智能数据分析
- 周报生成：自动生成酒店运营周报

## 自动构建镜像

本项目配置了 GitHub Actions 自动构建 Docker 镜像，同时推送到两个仓库：

### Docker Hub（推荐使用）
- 镜像地址：`binbin1213/hotelwebbi:latest`
- 无需域名前缀，使用更方便
- 全球最大的容器镜像仓库

### GitHub Container Registry
- 镜像地址：`ghcr.io/binbin1213/hotelwebbi:latest`
- 与 GitHub 仓库完全集成
- 免费使用

**构建触发条件：**
- 每次推送到 main 分支时自动构建
- 支持版本标签构建（如 `v1.0.0`）

详细部署指南请参考：[GITHUB_DEPLOYMENT.md](GITHUB_DEPLOYMENT.md)

## 注意事项

- 默认端口为5004，可以在docker-compose.yml中修改
- 系统数据存储在SQLite数据库中，确保数据库文件的权限正确
- 生产环境建议使用 GitHub 预构建镜像以获得更好的性能和稳定性
