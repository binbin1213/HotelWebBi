# 乐巷酒店数据智能分析系统 - 部署指南

## 🚀 一键部署脚本

新增了 `deploy.sh` 一键部署脚本，支持开发和生产环境的快速部署。

### 使用方法

**方式一：交互式菜单（推荐）**

```bash
# 给脚本执行权限
chmod +x deploy.sh

# 运行脚本，会显示选择菜单
./deploy.sh
```

会显示如下菜单：
```
=======================================
乐巷酒店数据智能分析系统
=======================================

请选择操作：

1) 开发环境启动 (本地测试)
2) 生产环境部署 (Docker)
3) 更新生产环境
4) 停止生产环境
5) 查看运行日志
6) 备份数据库
7) 显示帮助信息
0) 退出

请输入选项 [0-7]:
```

**方式二：直接命令（适合脚本调用）**

```bash
./deploy.sh dev     # 开发环境启动
./deploy.sh prod    # 生产环境部署
./deploy.sh update  # 更新生产环境
./deploy.sh stop    # 停止生产环境
./deploy.sh logs    # 查看日志
./deploy.sh backup  # 备份数据库
./deploy.sh help    # 查看帮助
```

## 📋 部署前准备

### 1. 环境变量配置

创建 `.env` 文件：

```bash
# DeepSeek API配置
DEEPSEEK_API_KEY=your_api_key_here
DEFAULT_MODEL=deepseek-reasoner

# 系统配置
TOTAL_ROOMS=29
DB_ADMIN_PASSWORD=your_admin_password

# 生产环境端口（可选）
PROD_PORT=5004
```

### 2. 系统要求

**开发环境：**
- Python 3.9+
- pip

**生产环境：**
- Docker
- Docker Compose

## 🔧 部署方案

### 方案一：开发环境（推荐用于测试）

```bash
./deploy.sh dev
```

**特点：**
- 自动创建虚拟环境
- 自动安装依赖
- 热重载支持
- 访问地址：http://localhost:5001

### 方案二：Docker生产环境（推荐用于生产）

```bash
./deploy.sh prod
```

**特点：**
- 容器化部署
- 自动重启
- 数据持久化
- 访问地址：http://localhost:5004

## 📁 项目结构

```
hotel-report-system/
├── deploy.sh              # 一键部署脚本 ⭐
├── docker-compose.prod.yml # 生产环境配置
├── Dockerfile             # Docker镜像配置
├── app.py                 # 主应用
├── ai_service.py          # AI服务
├── requirements.txt       # 依赖列表
├── .env                   # 环境变量（需创建）
├── static/                # 静态资源
├── templates/             # 模板文件
├── logs/                  # 日志目录
└── backups/               # 备份目录（自动创建）
```

## 🔄 更新部署

### 代码更新后

```bash
# 开发环境：重启即可
./deploy.sh dev

# 生产环境：更新部署
./deploy.sh update
```

### 依赖更新后

```bash
# 生产环境：完全重建
./deploy.sh stop
./deploy.sh prod
```

## 📊 监控和维护

### 查看服务状态

```bash
# 查看容器状态
docker-compose -f docker-compose.prod.yml ps

# 查看实时日志
./deploy.sh logs
```

### 数据备份

```bash
# 手动备份
./deploy.sh backup

# 定时备份（添加到crontab）
0 2 * * * cd /path/to/project && ./deploy.sh backup
```

### 故障排除

1. **服务启动失败**
   ```bash
   ./deploy.sh logs  # 查看错误日志
   ```

2. **端口冲突**
   - 修改 `docker-compose.prod.yml` 中的端口映射
   - 或停止占用端口的服务

3. **权限问题**
   ```bash
   sudo chown -R $USER:$USER .
   chmod +x deploy.sh
   ```

## 🌐 远程服务器部署

### 1. 上传代码

```bash
# 打包项目
tar -czf hotel-system.tar.gz --exclude=venv --exclude=__pycache__ --exclude=.git .

# 上传到服务器
scp hotel-system.tar.gz user@server:/path/to/deploy/

# 在服务器上解压
ssh user@server "cd /path/to/deploy && tar -xzf hotel-system.tar.gz"
```

### 2. 服务器部署

```bash
# SSH到服务器
ssh user@server

# 进入项目目录
cd /path/to/deploy

# 配置环境变量
cp .env.example .env
nano .env

# 部署
./deploy.sh prod
```

## 📝 注意事项

1. **首次部署**：确保已配置 `.env` 文件
2. **数据安全**：定期备份数据库文件
3. **端口管理**：确保部署端口未被占用
4. **日志监控**：定期查看应用日志
5. **更新策略**：生产环境更新前先在开发环境测试

## 🆘 技术支持

如遇到部署问题，请检查：
1. 环境变量配置是否正确
2. 端口是否被占用
3. Docker服务是否正常运行
4. 日志中的具体错误信息
