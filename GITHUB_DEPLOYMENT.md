# GitHub 自动构建镜像部署指南

本指南将帮助你使用 GitHub Actions 自动构建 Docker 镜像，并部署到生产环境。

## 1. GitHub Actions 自动构建设置

### 启用 GitHub Container Registry
1. 进入你的 GitHub 仓库：https://github.com/binbin1213/HotelWebBi
2. 点击 **Settings** 标签
3. 在左侧菜单中找到 **Actions** > **General**
4. 确保 **Actions permissions** 设置为允许运行 Actions

### 自动构建触发条件
GitHub Actions 会在以下情况自动构建镜像：
- 推送代码到 `main` 或 `master` 分支
- 创建新的版本标签（如 `v1.0.0`）
- 创建 Pull Request

## 2. 镜像标签说明

构建的镜像会自动推送到：`ghcr.io/binbin1213/hotelwebbi`

标签规则：
- `latest` - 最新的 main/master 分支版本
- `main` 或 `master` - 对应分支的最新版本
- `v1.0.0` - 版本标签（如果你创建了 git tag）

## 3. 生产环境部署

### 使用预构建镜像部署

1. **准备环境文件**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填入你的配置
   ```

2. **使用 GitHub 构建的镜像启动**
   ```bash
   docker-compose -f docker-compose.github.yml up -d
   ```

3. **查看运行状态**
   ```bash
   docker-compose -f docker-compose.github.yml ps
   docker-compose -f docker-compose.github.yml logs -f
   ```

### 更新到最新版本

```bash
# 拉取最新镜像
docker pull ghcr.io/binbin1213/hotelwebbi:latest

# 重启服务
docker-compose -f docker-compose.github.yml down
docker-compose -f docker-compose.github.yml up -d
```

## 4. 版本发布流程

### 创建新版本
```bash
# 创建并推送版本标签
git tag v1.0.0
git push origin v1.0.0
```

### 使用特定版本部署
修改 `docker-compose.github.yml` 中的镜像标签：
```yaml
services:
  hotel-analytics:
    image: ghcr.io/binbin1213/hotelwebbi:v1.0.0  # 使用特定版本
```

## 5. 监控构建状态

1. 进入 GitHub 仓库的 **Actions** 标签
2. 查看构建历史和状态
3. 点击具体的构建查看详细日志

## 6. 故障排除

### 构建失败
- 检查 Dockerfile 语法
- 确保 requirements.txt 中的依赖可以正常安装
- 查看 Actions 日志中的错误信息

### 镜像拉取失败
- 确保镜像已成功构建并推送
- 检查镜像名称和标签是否正确
- GitHub Container Registry 是公开的，无需认证

## 7. 本地测试

在推送到 GitHub 之前，可以本地测试构建：

```bash
# 本地构建镜像
docker build -t hotel-analytics:test .

# 本地运行测试
docker run -p 5004:5004 hotel-analytics:test
```

## 8. 环境变量配置

确保在生产环境中正确配置以下环境变量：

```bash
# .env 文件示例
DEEPSEEK_API_KEY=sk-your-actual-api-key
DEFAULT_MODEL=deepseek-reasoner
TOTAL_ROOMS=29
DB_ADMIN_PASSWORD=your-secure-password
```