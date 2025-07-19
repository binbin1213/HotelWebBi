#!/bin/bash

# 设置颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 设置API密钥环境变量
# 从.env文件加载环境变量
if [ -f ".env" ]; then
    echo -e "${GREEN}找到.env文件，正在加载环境变量...${NC}"
    while IFS= read -r line || [[ -n "$line" ]]; do
        # 忽略注释和空行
        [[ $line =~ ^#.*$ ]] && continue
        [[ -z "$line" ]] && continue
        
        # 解析变量
        key=$(echo "$line" | cut -d= -f1)
        value=$(echo "$line" | cut -d= -f2-)
        
        # 导出变量
        export "$key"="$value"
        echo -e "${GREEN}已加载环境变量: $key${NC}"
    done < .env
fi

# 检查API密钥
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo -e "${YELLOW}未检测到DEEPSEEK_API_KEY环境变量${NC}"
    echo -e "${YELLOW}请使用以下命令设置环境变量后再运行此脚本:${NC}"
    echo -e "${BLUE}export DEEPSEEK_API_KEY='your_api_key'${NC}"
    echo -e "${YELLOW}或者在运行脚本时直接设置:${NC}"
    echo -e "${BLUE}DEEPSEEK_API_KEY='your_api_key' ./start_app.sh${NC}"
    echo -e "${YELLOW}或者创建.env文件并添加DEEPSEEK_API_KEY=your_api_key${NC}"
    echo -e "${RED}是否继续运行? (系统将使用模拟AI响应) [y/N]${NC}"
    read -r continue_choice
    if [[ ! "$continue_choice" =~ ^[Yy]$ ]]; then
        echo -e "${RED}已取消启动.${NC}"
        exit 1
    fi
fi

# 显示欢迎信息
echo -e "${BLUE}=======================================${NC}"
echo -e "${GREEN}乐巷酒店数据智能分析系统启动脚本${NC}"
echo -e "${BLUE}=======================================${NC}"

# 检查是否存在虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}正在创建Python虚拟环境...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}创建虚拟环境失败，请确保已安装Python 3.${NC}"
        exit 1
    fi
fi

# 激活虚拟环境
echo -e "${YELLOW}正在激活虚拟环境...${NC}"
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}激活虚拟环境失败.${NC}"
    exit 1
fi

# 安装依赖
echo -e "${YELLOW}正在检查并安装依赖...${NC}"
pip install -r requirements.txt 2>/dev/null || {
    echo -e "${YELLOW}未找到requirements.txt，安装基本依赖...${NC}"
    pip install flask pandas numpy plotly openai
}

# 显示API密钥状态
if [ -n "$DEEPSEEK_API_KEY" ]; then
    masked_key="${DEEPSEEK_API_KEY:0:5}...${DEEPSEEK_API_KEY: -4}"
    echo -e "${GREEN}DeepSeek API密钥已配置: $masked_key${NC}"
else
    echo -e "${YELLOW}警告: API密钥未设置或为空${NC}"
    echo -e "${YELLOW}系统将使用模拟AI响应${NC}"
fi

# 启动应用
echo -e "${GREEN}正在启动乐巷酒店数据智能分析系统...${NC}"
echo -e "${BLUE}=======================================${NC}"
echo -e "${YELLOW}应用将在 http://localhost:5000 运行${NC}"
echo -e "${YELLOW}按 Ctrl+C 可以停止服务${NC}"
echo -e "${BLUE}=======================================${NC}"

python app.py 