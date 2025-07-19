import os
import json
import sqlite3
import pandas as pd
import re  # 添加正则表达式库
from openai import OpenAI  # 使用OpenAI SDK

# 读取.env文件
def load_env_file():
    """从.env文件加载环境变量"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        print(f"找到.env文件，正在加载...")
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key] = value
                    print(f"从.env加载环境变量: {key}")

# 加载.env文件
load_env_file()

# API配置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")  # 从环境变量获取API密钥
DEEPSEEK_BASE_URL = "https://api.deepseek.com"  # DeepSeek API基础URL
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")  # OpenAI API密钥

# 模型配置
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "deepseek-chat")  # 默认使用DeepSeek Chat模型
AVAILABLE_MODELS = {
    "deepseek-chat": {"base_url": DEEPSEEK_BASE_URL, "api_key": DEEPSEEK_API_KEY},
    "deepseek-coder": {"base_url": DEEPSEEK_BASE_URL, "api_key": DEEPSEEK_API_KEY},
    "deepseek-reasoner": {"base_url": DEEPSEEK_BASE_URL, "api_key": DEEPSEEK_API_KEY},
    "gpt-4o": {"base_url": None, "api_key": OPENAI_API_KEY},
    "gpt-4-turbo": {"base_url": None, "api_key": OPENAI_API_KEY}
}

# 启用调试模式
DEBUG = True

# 检查API密钥配置
def check_api_keys():
    """检查API密钥是否已配置，并打印相关信息"""
    if not DEEPSEEK_API_KEY:
        print("\033[91m警告: DEEPSEEK_API_KEY 未设置，将使用模拟响应\033[0m")
        print("\033[93m提示: 请在启动应用前设置环境变量 DEEPSEEK_API_KEY\033[0m")
        print("\033[93m      例如: export DEEPSEEK_API_KEY='your_api_key'\033[0m")
        return False
    elif DEEPSEEK_API_KEY.startswith("sk-") and len(DEEPSEEK_API_KEY) > 40:
        print(f"\033[93m警告: 您的API密钥格式可能不正确\033[0m")
        print(f"\033[93mDeepSeek API密钥通常以sk-开头，后跟32个字符\033[0m")
        print(f"\033[93m您可以在 https://platform.deepseek.com/api_keys 申请正确的API密钥\033[0m")
        print(f"\033[93m当前将使用您提供的API密钥: {DEEPSEEK_API_KEY[:5]}...{DEEPSEEK_API_KEY[-4:]}\033[0m")
        print(f"\033[93m如果遇到认证错误，请检查API密钥是否正确\033[0m")
        return True
    else:
        print(f"\033[92mDeepSeek API密钥已配置: {DEEPSEEK_API_KEY[:5]}...{DEEPSEEK_API_KEY[-4:]}\033[0m")
        return True
    
# 在模块加载时检查API密钥
api_keys_configured = check_api_keys()

# 数据库配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'hotel_revenue.db')

def get_database_schema():
    """获取数据库结构，用于提供给AI上下文"""
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='DailyRevenue'")
            schema = cursor.fetchone()[0]
            return schema
    except Exception as e:
        print(f"获取数据库结构出错: {e}")
        return "表结构获取失败"

def get_sample_data():
    """获取少量样本数据，用于提供给AI上下文"""
    try:
        with sqlite3.connect(DATABASE) as conn:
            df = pd.read_sql_query("SELECT * FROM DailyRevenue ORDER BY record_date DESC LIMIT 5", conn)
            return df.to_json(orient="records")
    except Exception as e:
        print(f"获取样本数据出错: {e}")
        return "[]"

def extract_json_from_markdown(text):
    """从可能包含Markdown代码块的文本中提取JSON内容"""
    # 安全检查
    if text is None:
        if DEBUG:
            print("警告: 输入文本为None")
        return ""
    
    if not isinstance(text, str):
        if DEBUG:
            print(f"警告: 输入文本不是字符串类型，而是 {type(text)}")
        return ""
    
    if not text.strip():
        if DEBUG:
            print("警告: 输入文本为空")
        return ""
    
    if DEBUG:
        print(f"原始响应内容长度: {len(text)}")
        print(f"原始响应前100字符: {text[0:100]}")
        print(f"原始响应后100字符: {text[-100:] if len(text) > 100 else text}")
    
    # 尝试查找Markdown格式的JSON代码块
    json_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    matches = re.findall(json_block_pattern, text)
    
    if matches and len(matches) > 0:
        # 使用找到的第一个代码块
        if DEBUG:
            print(f"从Markdown代码块中提取JSON: {matches[0][0:100]}")
        extracted_json = matches[0].strip()
        try:
            # 验证提取的内容是有效的JSON
            parsed_json = json.loads(extracted_json)
            if DEBUG:
                print("成功解析提取的JSON")
            return extracted_json
        except json.JSONDecodeError as e:
            if DEBUG:
                print(f"提取的内容不是有效JSON: {e}")
    else:
        if DEBUG:
            print("未找到Markdown代码块，检查其他格式")
    
    # 尝试查找可能的JSON对象，即使没有代码块标记
    if text.strip().startswith('{') and text.strip().endswith('}'):
        if DEBUG:
            print("找到可能的JSON对象，尝试直接解析")
        try:
            # 尝试解析它以验证它是否是有效的JSON
            json.loads(text.strip())
            return text.strip()
        except json.JSONDecodeError as e:
            if DEBUG:
                print(f"直接解析失败: {e}")
    
    # 尝试在文本中查找JSON对象
    json_pattern = r"(\{[\s\S]*\})"
    matches = re.findall(json_pattern, text)
    if matches and len(matches) > 0:
        if DEBUG:
            print(f"在文本中找到可能的JSON对象: {matches[0][0:100]}")
        try:
            # 尝试解析第一个匹配项以验证它是否是有效的JSON
            json.loads(matches[0].strip())
            return matches[0].strip()
        except json.JSONDecodeError as e:
            if DEBUG:
                print(f"正则匹配的JSON解析失败: {e}")
    
    # 如果没有找到代码块，返回原始文本
    if DEBUG:
        print("未找到有效的JSON格式内容，返回原始文本")
        if len(text) > 500:
            print(f"原始文本太长，只显示前500字符: {text[0:500]}...")
        else:
            print(f"原始文本: {text}")
    return text

def call_ai_api(user_query, model_name=None):
    """
    调用AI API进行自然语言处理
    
    参数:
        user_query: 用户的自然语言查询
        model_name: 要使用的模型名称，如果为None则使用默认模型
        
    返回:
        dict: 包含SQL查询、图表配置和分析洞察的字典
    """
    # 如果没有指定模型，使用默认模型
    if model_name is None:
        model_name = DEFAULT_MODEL
    
    # 检查模型是否可用
    if model_name not in AVAILABLE_MODELS:
        print(f"警告: 模型 {model_name} 不可用，使用默认模型 {DEFAULT_MODEL}")
        model_name = DEFAULT_MODEL
    
    # 获取模型配置
    model_config = AVAILABLE_MODELS[model_name]
    api_key = model_config["api_key"]
    base_url = model_config["base_url"]
    
    if not api_key:
        print(f"警告: 未设置 {model_name} 的API密钥，使用模拟响应")
        return simulate_ai_response(user_query)
    
    if DEBUG:
        print(f"正在处理查询: {user_query}")
        print(f"使用模型: {model_name}")
        print(f"使用API密钥: {api_key[:5]}...{api_key[-4:]}")
        print(f"API基础URL: {base_url}")
    
    # 获取数据库结构和样本数据作为上下文
    db_schema = get_database_schema()
    sample_data = get_sample_data()
    
    # 构建系统提示和用户消息
    system_prompt = "你是一名酒店数据分析师，请根据下方数据和问题，给出详细分析和建议。"
    
    # 构建用户消息，包含数据库结构和样本数据
    user_message = f"""
    查询: {user_query}
    
    数据库结构:
    {db_schema}
    
    样本数据(最近5条):
    {sample_data}
    
    请根据以上信息提供分析和建议。返回JSON格式如下:
    {{
        "sql": "查询SQL语句",
        "chart_type": "图表类型(如bar, line, pie等)",
        "x_field": "X轴字段",
        "y_field": "Y轴字段",
        "title": "分析标题",
        "dimensions": ["维度字段1", "维度字段2"],
        "metrics": ["指标字段1", "指标字段2"],
        "report_type": "报告类型(daily, weekly, monthly)",
        "insights": {{
            "summary": "总体分析",
            "key_findings": ["关键发现1", "关键发现2"],
            "anomalies": ["异常点1", "异常点2"],
            "recommendations": ["建议1", "建议2"]
        }}
    }}
    """
    
    try:
        if DEBUG:
            print("创建OpenAI客户端...")
        
        # 创建OpenAI客户端
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        if DEBUG:
            print("发送API请求...")
            print(f"用户消息: {user_message[:200]}...")
        
        # 发送请求
        try:
            response = client.chat.completions.create(
                model=model_name,  # 使用指定的模型
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1,  # 低温度以获得更确定性的结果
                max_tokens=1000
            )
            
            if DEBUG:
                print("成功获取API响应")
                print(f"响应状态: {response}")
            
            # 检查响应是否有效
            if not response or not hasattr(response, 'choices') or not response.choices:
                print("警告: API返回了空响应或无效响应")
                print(f"完整响应对象: {response}")
                return simulate_ai_response(user_query)
            
            # 获取响应内容
            ai_response = response.choices[0].message.content if response and hasattr(response, 'choices') and response.choices else None
            
            if DEBUG:
                print(f"AI响应是否为None: {ai_response is None}")
                print(f"AI响应类型: {type(ai_response)}")
                if ai_response:
                    print(f"AI原始响应内容长度: {len(ai_response)}")
                    if len(ai_response) > 0:
                        print(f"AI原始响应内容前200字符: {ai_response[0:200]}")
                    else:
                        print("AI原始响应内容为空字符串")
                else:
                    print("AI原始响应内容为None")
            
            # 如果响应为空，使用模拟响应
            if not ai_response:
                print("警告: API返回了空的响应内容，使用模拟响应")
                return simulate_ai_response(user_query)

            # 判断是否为JSON格式
            ai_response_str = ai_response.strip()
            # 首先尝试从Markdown中提取JSON内容
            json_content = extract_json_from_markdown(ai_response)
            
            try:
                # 尝试解析JSON内容
                parsed_response = json.loads(json_content)
                if DEBUG:
                    print("成功解析JSON响应")
                    return parsed_response
            except json.JSONDecodeError as e:
                # JSON解析失败，尝试修复或使用默认模板
                if DEBUG:
                    print(f"JSON解析错误: {e}")
                    print("尝试修复JSON格式或使用默认模板")
                
                # 尝试修复常见的JSON错误
                try:
                    # 修复单引号问题
                    fixed_content = json_content.replace("'", "\"")
                    parsed_response = json.loads(fixed_content)
                    if DEBUG:
                        print("修复JSON成功!")
                        return parsed_response
                except json.JSONDecodeError:
                    if DEBUG:
                        print("修复JSON失败，尝试使用默认JSON模板")
                    
                    # 尝试提取部分有效内容
                    try:
                        # 创建一个基本模板
                        template = {
                            "sql": "SELECT * FROM DailyRevenue",
                            "chart_type": "bar",
                            "x_field": "channel",
                            "y_field": "revenue",
                            "title": f"{user_query} - 分析结果",
                            "dimensions": ["channel"],
                            "metrics": ["revenue"],
                            "report_type": "daily",
                            "insights": {
                                "summary": "数据分析结果",
                                "key_findings": ["请查看图表和数据表格了解详细信息"],
                                "anomalies": [],
                                "recommendations": ["建议进一步分析数据"]
                            }
                        }
                        
                        # 尝试从响应中提取SQL语句
                        if json_content:
                            sql_match = re.search(r'"sql"\s*:\s*"([^"]+)"', json_content)
                            if sql_match:
                                template["sql"] = sql_match.group(1)
                            
                            # 尝试提取图表类型
                            chart_match = re.search(r'"chart_type"\s*:\s*"([^"]+)"', json_content)
                            if chart_match:
                                template["chart_type"] = chart_match.group(1)
                            
                            # 尝试提取标题
                            title_match = re.search(r'"title"\s*:\s*"([^"]+)"', json_content)
                            if title_match:
                                template["title"] = title_match.group(1)
                        
                        if DEBUG:
                            print("使用部分提取的内容创建响应")
                            return template
                    except Exception as extract_error:
                        if DEBUG:
                            print(f"无法提取部分内容: {extract_error}")
                            return simulate_ai_response(user_query)
            
            # 如果以上处理都失败，包装非JSON响应
            try:
                # 将非JSON响应安全包装在insights字段中
                if DEBUG:
                    print("返回非JSON响应，包装为insights字段")
                return {
                    "sql": "SELECT * FROM DailyRevenue ORDER BY record_date DESC LIMIT 100",
                    "chart_type": "bar",
                    "x_field": "channel",
                    "y_field": "revenue",
                    "title": f"{user_query} - 分析结果",
                    "insights": {
                        "summary": ai_response_str[:500],  # 限制长度，避免过长
                        "key_findings": ["请查看数据分析结果"],
                        "anomalies": [],
                        "recommendations": []
                    }
                }
            except Exception as wrapper_error:
                if DEBUG:
                    print(f"包装响应时出错: {wrapper_error}")
                return simulate_ai_response(user_query)
        except Exception as api_error:
            print(f"API调用过程中发生错误: {api_error}")
            print(f"错误类型: {type(api_error)}")
            print(f"错误详情: {str(api_error)}")
            return simulate_ai_response(user_query)
            
    except Exception as e:
        print(f"调用AI API出错: {e}")
        error_msg = str(e)
        if "401" in error_msg and "Authentication Fails" in error_msg:
            print("\033[91m认证失败: API密钥无效\033[0m")
            print("\033[93m请检查您的API密钥是否正确，或者尝试申请新的API密钥\033[0m")
            print("\033[93mDeepSeek API密钥可以在 https://platform.deepseek.com/api_keys 申请\033[0m")
        return simulate_ai_response(user_query)

# 为了向后兼容，保留原函数名
def call_deepseek_api(user_query):
    """向后兼容的函数，调用call_ai_api"""
    return call_ai_api(user_query)

def simulate_ai_response(user_query):
    """
    当API调用失败时模拟AI响应
    """
    # 简单关键词匹配
    parsed = {
        "sql": "SELECT * FROM DailyRevenue ORDER BY record_date DESC LIMIT 100",
        "chart_type": "bar",
        "x_field": "channel",
        "y_field": "revenue",
        "title": "销售渠道收入分析",
        "dimensions": ["channel"],
        "metrics": ["revenue"],
        "report_type": "daily",
        "insights": {
            "summary": "根据数据分析，不同渠道的收入和间夜数表现各异。",
            "key_findings": ["数据显示了销售渠道的收入情况。"],
            "anomalies": [],
            "recommendations": ["建议定期分析酒店数据，制定更有效的经营策略。"]
        }
    }
    
    # 渠道分析
    if "渠道" in user_query and "分布" in user_query:
        parsed["sql"] = """
            SELECT 
                channel, 
                SUM(revenue) as revenue,
                SUM(revenue) * 100.0 / (SELECT SUM(revenue) FROM DailyRevenue) as percentage 
            FROM DailyRevenue 
            GROUP BY channel 
            ORDER BY revenue DESC
        """
        parsed["chart_type"] = "pie"
        parsed["title"] = "销售渠道收入分布"
        parsed["dimensions"] = ["channel"]
        parsed["metrics"] = ["revenue", "percentage"]
    
    # 月度趋势分析
    elif "月度" in user_query and "趋势" in user_query:
        parsed["sql"] = """
            SELECT 
                substr(record_date, 1, 7) as month, 
                SUM(revenue) as revenue 
            FROM DailyRevenue 
            GROUP BY month 
            ORDER BY month
        """
        parsed["chart_type"] = "line"
        parsed["x_field"] = "month"
        parsed["title"] = "月度收入趋势"
        parsed["dimensions"] = ["month"]
        parsed["metrics"] = ["revenue"]
        parsed["report_type"] = "monthly"
    
    # 周度趋势分析
    elif ("周" in user_query or "星期" in user_query) and ("分布" in user_query or "趋势" in user_query):
        parsed["sql"] = """
            SELECT 
                strftime('%w', record_date) as day_of_week,
                CASE 
                    WHEN strftime('%w', record_date) = '0' THEN '周日'
                    WHEN strftime('%w', record_date) = '1' THEN '周一'
                    WHEN strftime('%w', record_date) = '2' THEN '周二'
                    WHEN strftime('%w', record_date) = '3' THEN '周三'
                    WHEN strftime('%w', record_date) = '4' THEN '周四'
                    WHEN strftime('%w', record_date) = '5' THEN '周五'
                    WHEN strftime('%w', record_date) = '6' THEN '周六'
                END as day_name,
                SUM(revenue) as revenue,
                SUM(room_nights) as room_nights,
                COUNT(DISTINCT record_date) as day_count
            FROM DailyRevenue 
            GROUP BY day_of_week
            ORDER BY day_of_week
        """
        parsed["chart_type"] = "bar"
        parsed["x_field"] = "day_name"
        parsed["y_field"] = "revenue"
        parsed["title"] = "一周内各天收入分布"
        parsed["dimensions"] = ["day_name"]
        parsed["metrics"] = ["revenue", "room_nights", "day_count"]
        parsed["report_type"] = "weekly"
    
    # 间夜数对比
    elif "间夜" in user_query and "对比" in user_query:
        parsed["sql"] = "SELECT channel, SUM(room_nights) as room_nights FROM DailyRevenue GROUP BY channel ORDER BY room_nights DESC"
        parsed["y_field"] = "room_nights"
        parsed["title"] = "渠道间夜数对比"
        parsed["metrics"] = ["room_nights"]
    
    # 平均房价分析
    elif "单价" in user_query or "房价" in user_query:
        parsed["sql"] = """
            SELECT 
                channel, 
                SUM(revenue)/SUM(room_nights) as avg_price 
            FROM DailyRevenue 
            GROUP BY channel 
            ORDER BY avg_price DESC
        """
        parsed["y_field"] = "avg_price"
        parsed["title"] = "渠道平均房价分析"
        parsed["metrics"] = ["avg_price"]
    
    # 多维度分析 - 渠道和星期
    elif "渠道" in user_query and ("星期" in user_query or "周" in user_query):
        parsed["sql"] = """
            SELECT 
                channel,
                strftime('%w', record_date) as day_of_week,
                SUM(revenue) as revenue,
                SUM(room_nights) as room_nights,
                SUM(revenue)/SUM(room_nights) as avg_price
            FROM DailyRevenue 
            GROUP BY channel, day_of_week
            ORDER BY channel, day_of_week
        """
        parsed["chart_type"] = "heatmap"
        parsed["title"] = "渠道和星期维度分析"
        parsed["dimensions"] = ["channel", "day_of_week"]
        parsed["metrics"] = ["revenue", "room_nights", "avg_price"]
    
    return parsed

def analyze_data_with_ai(query, data, model_name=None):
    """
    使用AI分析查询结果数据，生成洞察
    
    参数:
        query: 用户的原始查询
        data: 查询结果数据
        model_name: 要使用的模型名称，如果为None则使用默认模型
        
    返回:
        dict: 包含洞察分析的字典
    """
    # 如果没有指定模型，使用默认模型
    if model_name is None:
        model_name = DEFAULT_MODEL
    
    # 检查模型是否可用
    if model_name not in AVAILABLE_MODELS:
        print(f"警告: 模型 {model_name} 不可用，使用默认模型 {DEFAULT_MODEL}")
        model_name = DEFAULT_MODEL
    
    # 获取模型配置
    model_config = AVAILABLE_MODELS[model_name]
    api_key = model_config["api_key"]
    base_url = model_config["base_url"]
    
    if not api_key:
        print(f"警告: 未设置 {model_name} 的API密钥，使用模拟洞察")
        return simulate_insights(data)
    
    # 将数据转换为JSON字符串
    data_json = json.dumps(data.to_dict(orient="records"))
    
    # 构建系统提示和用户消息
    system_prompt = "你是一名酒店数据分析师，请根据下方数据和问题，给出详细分析和建议。"
    
    user_message = f"""
    用户查询: {query}
    
    查询结果数据:
    {data_json}
    
    请分析这些数据并提供洞察。请返回JSON格式如下:
    {{
        "summary": "总体分析",
        "key_findings": ["关键发现1", "关键发现2"],
        "anomalies": ["异常点1", "异常点2"],
        "recommendations": ["建议1", "建议2"],
        "comparisons": {{
            "channel_comparison": "渠道对比",
            "time_comparison": "时间对比",
            "growth_rates": {{
                "revenue_growth": "收入增长率",
                "room_nights_growth": "间夜增长率"
            }}
        }}
    }}
    """
    
    try:
        if DEBUG:
            print(f"创建OpenAI客户端进行数据分析，使用模型: {model_name}...")
        
        # 创建OpenAI客户端
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        if DEBUG:
            print("发送数据分析API请求...")
        
        # 发送请求
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        if DEBUG:
            print("成功获取数据分析API响应")
        
        # 获取响应内容
        ai_response = response.choices[0].message.content if response and hasattr(response, 'choices') and response.choices else None
        
        if DEBUG:
            print(f"数据分析原始响应: {ai_response[:200] if ai_response else 'None'}...")
        
        # 如果响应为空，使用模拟洞察
        if not ai_response:
            print("警告: AI返回了空的响应内容，使用模拟洞察")
            return simulate_insights(data)
            
        # 处理可能包含Markdown格式的响应
        json_content = extract_json_from_markdown(ai_response)
        
        if DEBUG:
            print(f"提取的数据分析JSON: {json_content[:200]}...")
        
        # 尝试解析JSON响应
        try:
            parsed_response = json.loads(json_content)
            return parsed_response
        except json.JSONDecodeError as e:
            print(f"AI返回的不是有效JSON: {json_content}")
            print(f"JSON解析错误: {e}")
            return simulate_insights(data)
            
    except Exception as e:
        print(f"调用AI API进行数据分析出错: {e}")
        error_msg = str(e)
        if "401" in error_msg and "Authentication Fails" in error_msg:
            print("\033[91m认证失败: API密钥无效\033[0m")
            print("\033[93m请检查您的API密钥是否正确，或者尝试申请新的API密钥\033[0m")
            print("\033[93mDeepSeek API密钥可以在 https://platform.deepseek.com/api_keys 申请\033[0m")
        return simulate_insights(data)

def standardize_channel_name(channel):
    """
    标准化渠道名称，将相似渠道合并
    """
    if channel in ['携程', '携程EBK']:
        return '携程'
    elif channel in ['美团', '美团EBK']:
        return '美团'
    elif channel in ['飞猪', '飞猪信用住']:
        return '飞猪'
    return channel

def simulate_insights(df):
    """模拟生成数据洞察"""
    insights = {
        "summary": "",
        "key_findings": [],
        "anomalies": [],
        "recommendations": [],
        "comparisons": {
            "channel_comparison": "",
            "time_comparison": "",
            "growth_rates": {
                "revenue_growth": "",
                "room_nights_growth": ""
            }
        }
    }
    
    try:
        # 如果数据中有渠道信息，标准化渠道名称
        if 'channel' in df.columns:
            df['channel'] = df['channel'].apply(standardize_channel_name)
            
        # 计算总收入
        if 'revenue' in df.columns:
            total_revenue = df['revenue'].sum()
            
            # 找出贡献最大的渠道
            if len(df) > 1:
                # 按收入排序
                df_sorted = df.sort_values('revenue', ascending=False)
                top_channel = df_sorted.iloc[0]
                bottom_channel = df_sorted.iloc[-1]
                
                # 计算百分比
                df['percentage'] = df['revenue'] / total_revenue * 100
                
                # 计算平均收入
                avg_revenue = total_revenue / len(df)
                
                # 更新总体趋势摘要
                top_channel_pct = float(top_channel['revenue']) / total_revenue * 100
                insights["summary"] = f"总收入为 {total_revenue:.2f} 元，其中{top_channel['channel']}渠道占比最高，达到{top_channel_pct:.2f}%。"
                
                # 添加关键发现
                insights["key_findings"].append(
                    f"{top_channel['channel']}是最主要收入来源，贡献了{float(top_channel['revenue']):.2f}元收入，占总收入的{top_channel_pct:.2f}%。"
                )
                
                # 添加排名信息
                channel_list = []
                for i, row in df_sorted.head(3).iterrows():
                    channel_list.append(f"{row['channel']}({float(row['revenue']):.2f}元)")
                
                if len(channel_list) > 0:
                    insights["key_findings"].append(
                        f"收入排名前{len(channel_list)}的渠道依次是：{', '.join(channel_list)}。"
                    )
                
                # 添加平均值信息
                insights["key_findings"].append(
                    f"平均每个渠道的收入为{avg_revenue:.2f}元。"
                )
                
                # 添加异常点分析
                for i, row in df_sorted.iterrows():
                    revenue = float(row['revenue'])
                    diff_from_avg = (revenue - avg_revenue) / avg_revenue * 100
                    
                    if diff_from_avg < -30:  # 显著低于平均值
                        insights["anomalies"].append(
                            f"{row['channel']}渠道收入显著低于平均值，仅为{revenue:.2f}元，低于平均值{abs(diff_from_avg):.2f}%。"
                        )
                    elif diff_from_avg > 50:  # 显著高于平均值
                        insights["anomalies"].append(
                            f"{row['channel']}渠道收入显著高于平均值，达到{revenue:.2f}元，高于平均值{diff_from_avg:.2f}%。"
                        )
                
                # 添加渠道对比
                if len(df) >= 2:
                    top_to_bottom_ratio = float(top_channel['revenue']) / float(bottom_channel['revenue']) if float(bottom_channel['revenue']) > 0 else 0
                    if top_to_bottom_ratio > 0:
                        insights["comparisons"]["channel_comparison"] = f"{top_channel['channel']}收入({float(top_channel['revenue']):.2f}元)是{bottom_channel['channel']}收入({float(bottom_channel['revenue']):.2f}元)的{top_to_bottom_ratio:.2f}倍。"
                
                # 添加建议
                insights["recommendations"].append(
                    f"增加对{top_channel['channel']}的投入，因为它贡献了最高的收入({float(top_channel['revenue']):.2f}元)且占比达到{top_channel_pct:.2f}%。"
                )

# 检查是否有月度数据
            if 'month' in df.columns and len(df) > 1:
                # 找出收入最高和最低的月份
                max_month = df.loc[df['revenue'].idxmax()]
                min_month = df.loc[df['revenue'].idxmin()]
                
                insights["key_findings"].append(
                    f"{max_month['month']}是收入最高的月份，为{float(max_month['revenue']):.2f}元。"
                )
                insights["key_findings"].append(
                    f"{min_month['month']}是收入最低的月份，为{float(min_month['revenue']):.2f}元。"
                )
                
                # 计算最高月与最低月的差异
                month_diff = (float(max_month['revenue']) - float(min_month['revenue'])) / float(min_month['revenue']) * 100 if float(min_month['revenue']) > 0 else 0
                if month_diff > 0:
                    insights["comparisons"]["time_comparison"] = f"{max_month['month']}收入比{min_month['month']}高{month_diff:.2f}%。"
                
                # 月度趋势
                if len(df) >= 3:
                    latest_months = df.sort_values('month', ascending=False).head(3)
                    if latest_months['revenue'].is_monotonic_decreasing:
                        last_month = latest_months.iloc[0]
                        first_month = latest_months.iloc[-1]
                        decrease_rate = (float(first_month['revenue']) - float(last_month['revenue'])) / float(first_month['revenue']) * 100 if float(first_month['revenue']) > 0 else 0
                        insights["anomalies"].append(f"最近三个月收入呈下降趋势，从{float(first_month['revenue']):.2f}元下降到{float(last_month['revenue']):.2f}元，下降了{decrease_rate:.2f}%，需要关注。")
                        insights["recommendations"].append(f"分析最近三个月收入下降的原因，制定措施扭转下降趋势。")
                    elif latest_months['revenue'].is_monotonic_increasing:
                        first_month = latest_months.iloc[-1]
                        last_month = latest_months.iloc[0]
                        growth_rate = (float(last_month['revenue']) - float(first_month['revenue'])) / float(first_month['revenue']) * 100 if float(first_month['revenue']) > 0 else 0
                        insights["key_findings"].append(f"最近三个月收入持续增长，从{float(first_month['revenue']):.2f}元增长到{float(last_month['revenue']):.2f}元，增长了{growth_rate:.2f}%。")
                        insights["comparisons"]["growth_rates"]["revenue_growth"] = f"最近三个月收入增长了{growth_rate:.2f}%。"
            
            # 检查是否有星期数据
            if 'day_of_week' in df.columns or 'day_name' in df.columns:
                day_field = 'day_name' if 'day_name' in df.columns else 'day_of_week'
                
                # 工作日与周末对比
                weekday_values = ['周一', '周二', '周三', '周四', '周五', '1', '2', '3', '4', '5']
                weekend_values = ['周六', '周日', '0', '6']
                
                weekday_data = df[df[day_field].isin(weekday_values)]
                weekend_data = df[df[day_field].isin(weekend_values)]
                
                if not weekday_data.empty and not weekend_data.empty:
                    weekday_revenue = weekday_data['revenue'].sum()
                    weekend_revenue = weekend_data['revenue'].sum()
                    
                    weekday_days = len(weekday_data)
                    weekend_days = len(weekend_data)
                    
                    # 计算日均收入
                    weekday_daily_avg = weekday_revenue / weekday_days if weekday_days > 0 else 0
                    weekend_daily_avg = weekend_revenue / weekend_days if weekend_days > 0 else 0
                    
                    # 比较日均收入
                    if weekend_daily_avg > weekday_daily_avg and weekday_daily_avg > 0:
                        diff_pct = (weekend_daily_avg - weekday_daily_avg) / weekday_daily_avg * 100
                        insights["comparisons"]["time_comparison"] = f"周末日均收入({weekend_daily_avg:.2f}元)比工作日({weekday_daily_avg:.2f}元)高{diff_pct:.2f}%。"
                        insights["key_findings"].append(f"周末表现更好，日均收入为{weekend_daily_avg:.2f}元，比工作日高{diff_pct:.2f}%。")
                        insights["recommendations"].append(f"针对工作日制定特别促销活动，提高工作日入住率。")
                    elif weekday_daily_avg > weekend_daily_avg and weekend_daily_avg > 0:
                        diff_pct = (weekday_daily_avg - weekend_daily_avg) / weekend_daily_avg * 100
                        insights["comparisons"]["time_comparison"] = f"工作日日均收入({weekday_daily_avg:.2f}元)比周末({weekend_daily_avg:.2f}元)高{diff_pct:.2f}%。"
                        insights["key_findings"].append(f"工作日表现更好，日均收入为{weekday_daily_avg:.2f}元，比周末高{diff_pct:.2f}%。")
                        insights["recommendations"].append(f"开发更多周末休闲项目，吸引周末客源。")
        
        # 间夜数相关洞察
        if 'room_nights' in df.columns:
            total_nights = df['room_nights'].sum()
            
            if 'revenue' in df.columns and total_nights > 0:
                avg_price = df['revenue'].sum() / total_nights
                insights["key_findings"].append(f"平均每间夜收入为{avg_price:.2f}元。")
            
            if 'channel' in df.columns and len(df) > 1:
                # 找出间夜数最多的渠道
                top_nights_channel = df.sort_values('room_nights', ascending=False).iloc[0]
                top_nights_pct = float(top_nights_channel['room_nights']) / total_nights * 100 if total_nights > 0 else 0
                
                insights["key_findings"].append(
                    f"{top_nights_channel['channel']}贡献了最多的间夜数：{int(top_nights_channel['room_nights'])}间夜，占总间夜数的{top_nights_pct:.2f}%。"
                )
        
        # 平均单价相关洞察
        if 'avg_price' in df.columns and len(df) > 1:
            # 找出单价最高的渠道
            df_sorted = df.sort_values('avg_price', ascending=False)
            top_price_channel = df_sorted.iloc[0]
            lowest_price_channel = df_sorted.iloc[-1]
            
            insights["key_findings"].append(
                f"{top_price_channel['channel']}的平均单价最高，为{float(top_price_channel['avg_price']):.2f}元。"
            )
            
            # 计算平均单价差异
            price_diff = float(top_price_channel['avg_price']) - float(lowest_price_channel['avg_price'])
            price_diff_pct = price_diff / float(lowest_price_channel['avg_price']) * 100 if float(lowest_price_channel['avg_price']) > 0 else 0
            
            if price_diff_pct > 30:
                insights["anomalies"].append(
                    f"{top_price_channel['channel']}和{lowest_price_channel['channel']}的单价差异较大，达到{price_diff_pct:.1f}%。"
                )
                insights["recommendations"].append(
                    f"分析{lowest_price_channel['channel']}渠道的低单价原因，考虑调整定价策略或提升产品档次。"
                )
        
        # 如果没有生成足够的建议，添加一些通用建议
        if len(insights["recommendations"]) < 2:
            insights["recommendations"].append(
                "定期分析各渠道的收入和间夜数据，根据市场变化及时调整营销策略。"
            )
            insights["recommendations"].append(
                "加强与表现良好渠道的合作，同时开发新的销售渠道，分散风险。"
            )
        
        return insights
    except Exception as e:
        print(f"生成模拟洞察时出错: {e}")
        # 返回一个基本的洞察结构
        return {
            "summary": "数据分析过程中出现问题，无法生成完整洞察。请检查数据格式或重试。",
            "key_findings": ["数据可能存在格式问题，请检查数据完整性。"],
            "anomalies": [],
            "recommendations": ["建议重新执行查询或联系系统管理员。"],
            "comparisons": {
                "channel_comparison": "",
                "time_comparison": "",
                "growth_rates": {
                    "revenue_growth": "",
                    "room_nights_growth": ""
                }
            }
        } 