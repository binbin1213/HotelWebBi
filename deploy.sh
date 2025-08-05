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

# 交互式菜单
show_menu() {
    echo -e "${BLUE}=======================================${NC}"
    echo -e "${GREEN}乐巷酒店数据智能分析系统${NC}"
    echo -e "${BLUE}=======================================${NC}"
    echo ""
    echo "请选择操作："
    echo ""
    echo -e "${YELLOW}1)${NC} 拉取最新代码"
    echo -e "${YELLOW}2)${NC} 开发环境启动 (本地测试)"
    echo -e "${YELLOW}3)${NC} 生产环境部署 (Docker)"
    echo -e "${YELLOW}4)${NC} 更新生产环境"
    echo -e "${YELLOW}5)${NC} 停止生产环境"
    echo -e "${YELLOW}6)${NC} 查看运行日志"
    echo -e "${YELLOW}7)${NC} 备份数据库"
    echo -e "${YELLOW}8)${NC} 显示帮助信息"
    echo -e "${YELLOW}0)${NC} 退出"
    echo ""
    echo -n -e "${GREEN}请输入选项 [0-8]: ${NC}"
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

# 拉取最新代码
pull_code() {
    echo -e "${YELLOW}正在拉取最新代码...${NC}"

    # 检查是否是git仓库
    if [ ! -d ".git" ]; then
        echo -e "${RED}错误: 当前目录不是git仓库${NC}"
        return 1
    fi

    # 检查是否有未提交的更改
    if ! git diff-index --quiet HEAD --; then
        echo -e "${YELLOW}检测到未提交的更改，正在暂存...${NC}"
        git stash push -m "Auto stash before pull $(date)"
        stashed=true
    else
        stashed=false
    fi

    # 拉取最新代码
    if git pull origin main; then
        echo -e "${GREEN}✓ 代码拉取成功${NC}"

        # 如果之前暂存了更改，询问是否恢复
        if [ "$stashed" = true ]; then
            echo -e "${YELLOW}是否恢复之前暂存的更改? [y/N]${NC}"
            read -r restore_choice
            if [[ "$restore_choice" =~ ^[Yy]$ ]]; then
                git stash pop
                echo -e "${GREEN}✓ 已恢复暂存的更改${NC}"
            else
                echo -e "${YELLOW}暂存的更改保留在stash中，可用 'git stash pop' 恢复${NC}"
            fi
        fi
        return 0
    else
        echo -e "${RED}✗ 代码拉取失败${NC}"

        # 如果拉取失败且有暂存，恢复暂存
        if [ "$stashed" = true ]; then
            git stash pop
            echo -e "${YELLOW}已恢复暂存的更改${NC}"
        fi
        return 1
    fi
}

# 开发环境启动
start_dev() {
    echo -e "${BLUE}=======================================${NC}"
    echo -e "${GREEN}启动开发环境${NC}"
    echo -e "${BLUE}=======================================${NC}"

    check_env

    # 简单启动
    echo -e "${GREEN}启动应用...${NC}"
    echo -e "${YELLOW}访问地址: http://localhost:5001${NC}"
    echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"
    echo ""
    python app.py
}

# 生产环境部署
deploy_prod() {
    echo -e "${BLUE}=======================================${NC}"
    echo -e "${GREEN}部署到生产环境${NC}"
    echo -e "${BLUE}=======================================${NC}"

    # 拉取最新代码
    if ! pull_code; then
        echo -e "${YELLOW}代码拉取失败，是否继续部署? [y/N]${NC}"
        read -r continue_choice
        if [[ ! "$continue_choice" =~ ^[Yy]$ ]]; then
            echo -e "${RED}已取消部署${NC}"
            return 1
        fi
    fi

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

    # 拉取最新代码
    if ! pull_code; then
        echo -e "${YELLOW}代码拉取失败，是否继续更新? [y/N]${NC}"
        read -r continue_choice
        if [[ ! "$continue_choice" =~ ^[Yy]$ ]]; then
            echo -e "${RED}已取消更新${NC}"
            return 1
        fi
    fi

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

# 处理用户选择
handle_choice() {
    case $1 in
        1)
            start_dev
            ;;
        2)
            deploy_prod
            ;;
        3)
            update_prod
            ;;
        4)
            stop_prod
            ;;
        5)
            show_logs
            ;;
        6)
            backup_db
            ;;
        7)
            show_help
            ;;
        0)
            echo -e "${GREEN}再见！${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}无效选项，请重新选择${NC}"
            return 1
            ;;
    esac
}

# 主逻辑
if [ $# -eq 0 ]; then
    # 没有参数时显示交互式菜单
    while true; do
        show_menu
        read -r choice
        echo ""

        if handle_choice "$choice"; then
            echo ""
            echo -e "${YELLOW}操作完成！按回车键继续...${NC}"
            read -r
        fi
        echo ""
    done
else
    # 有参数时直接执行对应命令
    case "${1}" in
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
fi
