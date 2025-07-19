# 乐巷酒店数据智能分析系统 - Docker部署指南

这个项目是乐巷酒店的数据智能分析系统，集成了数据管理、可视化分析和AI智能分析功能。本指南将帮助您使用Docker部署该系统。

## 系统要求

- Docker
- Docker Compose

## 快速部署

### 1. 克隆代码库

```bash
git clone <repository-url>
cd hotel
```

### 2. 构建并启动Docker容器

```bash
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

## 注意事项

- 默认端口为5004，可以在docker-compose.yml中修改
- 系统数据存储在SQLite数据库中，确保数据库文件的权限正确 