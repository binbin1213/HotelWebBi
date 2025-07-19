# 服务器部署步骤

## 1. 传输压缩包到服务器

```bash
# 将压缩包传输到服务器
scp hotel_deploy.tar.gz 用户名@服务器IP:/home/binbin/
```

## 2. 解压文件并设置目录结构

登录到服务器后执行：

```bash
# 登录服务器
ssh 用户名@服务器IP

# 进入目录
cd /home/binbin/

# 解压文件
tar -xzvf hotel_deploy.tar.gz

# 创建hotel_data目录（如果不存在）
mkdir -p /home/binbin/hotel_data/logs

# 将文件移动到正确位置
cp -r deploy_package/app.py deploy_package/ai_service.py /home/binbin/hotel_data/
cp -r deploy_package/Dockerfile deploy_package/docker-compose.yml deploy_package/requirements.txt /home/binbin/hotel_data/
cp -r deploy_package/.env /home/binbin/hotel_data/
cp -r deploy_package/static /home/binbin/hotel_data/
cp -r deploy_package/templates /home/binbin/hotel_data/

# 修改目录权限（确保容器可以访问）
chmod -R 755 /home/binbin/hotel_data
```

## 3. 构建和启动容器

```bash
# 进入项目目录
cd /home/binbin/hotel_data

# 构建镜像
docker-compose build

# 启动容器
docker-compose up -d

# 查看日志确认运行状态
docker-compose logs -f
```

## 4. 验证部署

访问 http://服务器IP:5004 检查应用是否正常运行。

## 5. 清理临时文件（可选）

```bash
# 删除解压后的临时文件
rm -rf /home/binbin/deploy_package
rm /home/binbin/hotel_deploy.tar.gz
```

## 6. 更新应用（未来需要时）

如果需要更新应用：

1. 本地打包新版本：
```bash
tar -czvf hotel_update.tar.gz 需要更新的文件...
```

2. 上传到服务器：
```bash
scp hotel_update.tar.gz 用户名@服务器IP:/home/binbin/
```

3. 在服务器上解压并替换文件
4. Gunicorn会自动重新加载应用 