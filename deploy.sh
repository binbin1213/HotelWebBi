#!/bin/bash

# 乐巷酒店数据智能分析系统 - 一键部署脚本
# 支持本地开发和Docker生产环境部署

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示帮助信息
show_help() {
    echo -e "${BLUE}乐巷酒店数据智能分析系统 - 部署脚本${NC}"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  dev     - 本地开发环境启动"
    echo "  prod    - Docker生产环境部署"
    echo "  update  - 更新生产环境代码"
    echo "  stop    - 停止生产环境服务"
    echo "  logs    - 查看生产环境日志"
    echo "  backup  - 备份数据库"
    echo "  help    - 显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 dev      # 启动开发环境"
    echo "  $0 prod     # 部署到生产环境"
    echo "  $0 update   # 更新生产环境"
}

# 检查环境变量
check_env() {
    if [ -f ".env" ]; then
        echo -e "${GREEN}找到.env文件，正在加载环境变量...${NC}"
        set -a  # 自动导出变量
        source .env
        set +a
        echo -e "${GREEN}环境变量加载完成${NC}"
    else
        echo -e "${YELLOW}警告: 未找到.env文件${NC}"
        echo -e "${YELLOW}请创建.env文件并配置必要的环境变量${NC}"
    fi
}

# 开发环境启动
start_dev() {
    echo -e "${BLUE}=======================================${NC}"
    echo -e "${GREEN}启动开发环境${NC}"
    echo -e "${BLUE}=======================================${NC}"
    
    check_env
    
    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}创建Python虚拟环境...${NC}"
        python3 -m venv venv
    fi
    
    # 激活虚拟环境
    echo -e "${YELLOW}激活虚拟环境...${NC}"
    source venv/bin/activate
    
    # 安装依赖
    echo -e "${YELLOW}安装依赖...${NC}"
    pip install -r requirements.txt
    
    # 启动应用
    echo -e "${GREEN}启动应用...${NC}"
    echo -e "${YELLOW}访问地址: http://localhost:5001${NC}"
    echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"
    python app.py
}

# 生产环境部署
deploy_prod() {
    echo -e "${BLUE}=======================================${NC}"
    echo -e "${GREEN}部署到生产环境${NC}"
    echo -e "${BLUE}=======================================${NC}"
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}错误: 未安装Docker${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}错误: 未安装Docker Compose${NC}"
        exit 1
    fi
    
    # 停止现有服务
    echo -e "${YELLOW}停止现有服务...${NC}"
    docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
    
    # 构建镜像
    echo -e "${YELLOW}构建Docker镜像...${NC}"
    docker-compose -f docker-compose.prod.yml build
    
    # 启动服务
    echo -e "${YELLOW}启动服务...${NC}"
    docker-compose -f docker-compose.prod.yml up -d
    
    # 等待服务启动
    echo -e "${YELLOW}等待服务启动...${NC}"
    sleep 5
    
    # 检查服务状态
    if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
        echo -e "${GREEN}✓ 服务启动成功${NC}"
        echo -e "${YELLOW}访问地址: http://localhost:5004${NC}"
    else
        echo -e "${RED}✗ 服务启动失败${NC}"
        echo -e "${YELLOW}查看日志: $0 logs${NC}"
        exit 1
    fi
}

# 更新生产环境
update_prod() {
    echo -e "${BLUE}=======================================${NC}"
    echo -e "${GREEN}更新生产环境${NC}"
    echo -e "${BLUE}=======================================${NC}"
    
    # 重新构建并启动
    echo -e "${YELLOW}重新构建镜像...${NC}"
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    echo -e "${YELLOW}重启服务...${NC}"
    docker-compose -f docker-compose.prod.yml up -d
    
    echo -e "${GREEN}✓ 更新完成${NC}"
}

# 停止生产环境
stop_prod() {
    echo -e "${YELLOW}停止生产环境服务...${NC}"
    docker-compose -f docker-compose.prod.yml down
    echo -e "${GREEN}✓ 服务已停止${NC}"
}

# 查看日志
show_logs() {
    echo -e "${YELLOW}显示生产环境日志...${NC}"
    docker-compose -f docker-compose.prod.yml logs -f
}

# 备份数据库
backup_db() {
    echo -e "${YELLOW}备份数据库...${NC}"
    
    # 创建备份目录
    mkdir -p backups
    
    # 生成备份文件名
    backup_file="backups/hotel_revenue_$(date +%Y%m%d_%H%M%S).db"
    
    # 复制数据库文件
    if [ -f "hotel_revenue.db" ]; then
        cp hotel_revenue.db "$backup_file"
        echo -e "${GREEN}✓ 数据库备份完成: $backup_file${NC}"
    else
        echo -e "${RED}✗ 未找到数据库文件${NC}"
        exit 1
    fi
}

# 主逻辑
case "${1:-help}" in
    "dev")
        start_dev
        ;;
    "prod")
        deploy_prod
        ;;
    "update")
        update_prod
        ;;
    "stop")
        stop_prod
        ;;
    "logs")
        show_logs
        ;;
    "backup")
        backup_db
        ;;
    "help"|*)
        show_help
        ;;
esac
