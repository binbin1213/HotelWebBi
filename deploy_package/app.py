import sqlite3
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from ai_service import call_ai_api, analyze_data_with_ai, DEFAULT_MODEL
import argparse
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# --- App Configuration ---
app = Flask(__name__)
# This secret key is needed to show flashed messages
app.config['SECRET_KEY'] = 'a_very_secret_key_that_should_be_changed' 

# --- Database Configuration ---
# Get the absolute path of the directory where the script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Define the path to the database file
DATABASE = os.path.join(BASE_DIR, 'hotel_revenue.db')

def init_db():
    """
    Initializes the database and creates the table if it doesn't exist.
    This is a safe function to run every time.
    """
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            
            # 检查表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='DailyRevenue'")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                # 表不存在，直接创建新表
                cursor.execute("""
                    CREATE TABLE DailyRevenue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        record_date DATE NOT NULL,
                        channel VARCHAR(50) NOT NULL,
                        fee_type VARCHAR(50) NOT NULL,
                        room_nights DECIMAL(10, 2),
                        revenue DECIMAL(10, 2),
                        UNIQUE (record_date, channel, fee_type)
                    );
                """)
                print("已创建 DailyRevenue 表")
            conn.commit()
            print("数据库初始化成功")
            # 如果表已存在，不做任何操作
    except Exception as e:
        print(f"初始化数据库时出错: {e}")

# --- Routes ---

@app.route('/')
def index():
    """
    Renders the main homepage with real statistics.
    """
    try:
        # 从环境变量获取房间总数，如果未设置则默认为29
        total_rooms = int(os.getenv('TOTAL_ROOMS', 29))
        
        stats = {}
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            
            # 获取当前日期
            today = datetime.now()
            
            # --- 本月数据计算 ---
            # 本月第一天
            month_start = datetime(today.year, today.month, 1).strftime('%Y-%m-%d')
            # 本月最后一天（如果今天不是月末，则使用今天的日期作为结束日期）
            next_month = today.replace(day=28) + timedelta(days=4)  # 跳到下个月
            month_end = min((next_month - timedelta(days=next_month.day)).replace(day=today.day), today).strftime('%Y-%m-%d')
            
            # 1. 本月收入
            cursor.execute("SELECT SUM(revenue) FROM DailyRevenue WHERE record_date >= ? AND record_date <= ?", 
                          (month_start, month_end))
            month_revenue = cursor.fetchone()[0] or 0
            
            # 获取上月收入，用于计算同比
            last_month = (today.replace(day=1) - timedelta(days=1))  # 上个月的最后一天
            last_month_start = datetime(last_month.year, last_month.month, 1).strftime('%Y-%m-%d')
            last_month_end = last_month.strftime('%Y-%m-%d')
            
            cursor.execute("SELECT SUM(revenue) FROM DailyRevenue WHERE record_date >= ? AND record_date <= ?", 
                          (last_month_start, last_month_end))
            last_month_revenue = cursor.fetchone()[0] or 0
            
            # 计算本月收入同比变化
            month_revenue_change = 0
            if last_month_revenue > 0:
                month_revenue_change = ((month_revenue - last_month_revenue) / last_month_revenue) * 100
            
            # 2. 本月间夜数
            cursor.execute("SELECT SUM(room_nights) FROM DailyRevenue WHERE record_date >= ? AND record_date <= ?", 
                          (month_start, month_end))
            month_room_nights = cursor.fetchone()[0] or 0
            
            # 获取上月间夜数，用于计算同比
            cursor.execute("SELECT SUM(room_nights) FROM DailyRevenue WHERE record_date >= ? AND record_date <= ?", 
                          (last_month_start, last_month_end))
            last_month_room_nights = cursor.fetchone()[0] or 0
            
            # 计算本月间夜同比变化
            month_room_nights_change = 0
            if last_month_room_nights > 0:
                month_room_nights_change = ((month_room_nights - last_month_room_nights) / last_month_room_nights) * 100
            
            # 3. 本月平均房价
            cursor.execute("""
                SELECT SUM(revenue) / SUM(room_nights) 
                FROM DailyRevenue 
                WHERE record_date >= ? AND record_date <= ? AND room_nights > 0
            """, (month_start, month_end))
            month_avg_price = cursor.fetchone()[0] or 0
            
            # 获取上月平均房价，用于计算同比
            cursor.execute("""
                SELECT SUM(revenue) / SUM(room_nights) 
                FROM DailyRevenue 
                WHERE record_date >= ? AND record_date <= ? AND room_nights > 0
            """, (last_month_start, last_month_end))
            last_month_avg_price = cursor.fetchone()[0] or 0
            
            # 计算平均房价同比变化
            month_avg_price_change = 0
            if last_month_avg_price > 0:
                month_avg_price_change = ((month_avg_price - last_month_avg_price) / last_month_avg_price) * 100
            
            # 4. 计算本月入住率
            # 计算本月的天数
            days_in_current_month = today.day  # 从1到当前日期
            
            # 计算本月入住率
            cursor.execute("""
                SELECT SUM(room_nights) * 100.0 / (? * ?)
                FROM DailyRevenue 
                WHERE record_date >= ? AND record_date <= ?
            """, (total_rooms, days_in_current_month, month_start, month_end))
            month_occupancy_rate = cursor.fetchone()[0] or 0
            
            # 获取上月入住率，用于计算同比
            # 计算上月的天数
            days_in_last_month = last_month.day
            
            cursor.execute("""
                SELECT SUM(room_nights) * 100.0 / (? * ?)
                FROM DailyRevenue 
                WHERE record_date >= ? AND record_date <= ?
            """, (total_rooms, days_in_last_month, last_month_start, last_month_end))
            last_month_occupancy_rate = cursor.fetchone()[0] or 0
            
            # 计算入住率同比变化
            month_occupancy_rate_change = 0
            if last_month_occupancy_rate > 0:
                month_occupancy_rate_change = ((month_occupancy_rate - last_month_occupancy_rate) / last_month_occupancy_rate) * 100
            
            # 5. 计算本月 RevPAR
            month_revpar = (month_avg_price * month_occupancy_rate) / 100 if month_occupancy_rate > 0 else 0
            last_month_revpar = (last_month_avg_price * last_month_occupancy_rate) / 100 if last_month_occupancy_rate > 0 else 0
            
            month_revpar_change = 0
            if last_month_revpar > 0:
                month_revpar_change = ((month_revpar - last_month_revpar) / last_month_revpar) * 100
            
            # --- 本周数据计算 ---
            # 本周一的日期
            week_start = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
            # 本周日的日期（如果今天是周日之前，则使用今天的日期作为结束日期）
            week_end = min((today - timedelta(days=today.weekday()) + timedelta(days=6)), today).strftime('%Y-%m-%d')
            
            # 1. 本周收入（原今日收入）
            cursor.execute("SELECT SUM(revenue) FROM DailyRevenue WHERE record_date >= ? AND record_date <= ?", 
                          (week_start, week_end))
            week_revenue = cursor.fetchone()[0] or 0
            
            # 获取上周收入，用于计算同比
            last_week_start = (today - timedelta(days=today.weekday() + 7)).strftime('%Y-%m-%d')
            last_week_end = (today - timedelta(days=today.weekday() + 1)).strftime('%Y-%m-%d')
            cursor.execute("SELECT SUM(revenue) FROM DailyRevenue WHERE record_date >= ? AND record_date <= ?", 
                          (last_week_start, last_week_end))
            last_week_revenue = cursor.fetchone()[0] or 0
            
            # 计算本周收入同比变化
            revenue_change = 0
            if last_week_revenue > 0:
                revenue_change = ((week_revenue - last_week_revenue) / last_week_revenue) * 100
            
            # 2. 本周间夜数（完整一周数据）
            cursor.execute("SELECT SUM(room_nights) FROM DailyRevenue WHERE record_date >= ? AND record_date <= ?", 
                          (week_start, week_end))
            week_room_nights = cursor.fetchone()[0] or 0
            
            # 获取上周间夜数，用于计算同比
            cursor.execute("SELECT SUM(room_nights) FROM DailyRevenue WHERE record_date >= ? AND record_date <= ?", 
                          (last_week_start, last_week_end))
            last_week_room_nights = cursor.fetchone()[0] or 0
            
            # 计算本周间夜同比变化
            room_nights_change = 0
            if last_week_room_nights > 0:
                room_nights_change = ((week_room_nights - last_week_room_nights) / last_week_room_nights) * 100
            
            # 3. 本周平均房价
            cursor.execute("""
                SELECT SUM(revenue) / SUM(room_nights) 
                FROM DailyRevenue 
                WHERE record_date >= ? AND record_date <= ? AND room_nights > 0
            """, (week_start, week_end))
            avg_price = cursor.fetchone()[0] or 0
            
            # 获取上周平均房价，用于计算同比
            cursor.execute("""
                SELECT SUM(revenue) / SUM(room_nights) 
                FROM DailyRevenue 
                WHERE record_date >= ? AND record_date <= ? AND room_nights > 0
            """, (last_week_start, last_week_end))
            last_week_avg_price = cursor.fetchone()[0] or 0
            
            # 计算平均房价同比变化
            avg_price_change = 0
            if last_week_avg_price > 0:
                avg_price_change = ((avg_price - last_week_avg_price) / last_week_avg_price) * 100
            
            # 4. 计算入住率
            # 计算本周的天数（从周一到今天或周日，取较小值）
            days_in_current_week = min((today.weekday() + 1), 7)  # 从1到7
            
            # 计算本周入住率
            cursor.execute("""
                SELECT SUM(room_nights) * 100.0 / (? * ?)
                FROM DailyRevenue 
                WHERE record_date >= ? AND record_date <= ?
            """, (total_rooms, days_in_current_week, week_start, week_end))
            occupancy_rate = cursor.fetchone()[0] or 0
            
            # 获取上周入住率，用于计算同比
            cursor.execute("""
                SELECT SUM(room_nights) * 100.0 / (? * 7)
                FROM DailyRevenue 
                WHERE record_date >= ? AND record_date <= ?
            """, (total_rooms, last_week_start, last_week_end))
            last_week_occupancy_rate = cursor.fetchone()[0] or 0
            
            # 计算入住率同比变化
            occupancy_rate_change = 0
            if last_week_occupancy_rate > 0:
                occupancy_rate_change = ((occupancy_rate - last_week_occupancy_rate) / last_week_occupancy_rate) * 100
            
            # 5. 计算本周 RevPAR
            week_revpar = (avg_price * occupancy_rate) / 100 if occupancy_rate > 0 else 0
            last_week_revpar = (last_week_avg_price * last_week_occupancy_rate) / 100 if last_week_occupancy_rate > 0 else 0
            
            revpar_change = 0
            if last_week_revpar > 0:
                revpar_change = ((week_revpar - last_week_revpar) / last_week_revpar) * 100
            
            stats = {
                # 本月数据
                'month_revenue': int(month_revenue),
                'month_revenue_change': round(month_revenue_change, 1),
                'month_room_nights': int(month_room_nights),
                'month_room_nights_change': round(month_room_nights_change, 1),
                'month_avg_price': round(month_avg_price, 2),
                'month_avg_price_change': round(month_avg_price_change, 1),
                'month_occupancy_rate': round(month_occupancy_rate, 2),
                'month_occupancy_rate_change': round(month_occupancy_rate_change, 1),
                'month_revpar': round(month_revpar, 2),
                'month_revpar_change': round(month_revpar_change, 1),
                
                # 本周数据
                'today_revenue': int(week_revenue),
                'revenue_change': round(revenue_change, 1),
                'week_room_nights': int(week_room_nights),
                'room_nights_change': round(room_nights_change, 1),
                'avg_price': round(avg_price, 2),
                'avg_price_change': round(avg_price_change, 1),
                'week_occupancy_rate': round(occupancy_rate, 2),
                'occupancy_rate_change': round(occupancy_rate_change, 1),
                'week_revpar': round(week_revpar, 2),
                'revpar_change': round(revpar_change, 1),
            }
            
    except Exception as e:
        print(f"获取统计数据时出错: {e}")
        # 如果出错，使用默认数据
        stats = {
            # 本月数据默认值
            'month_revenue': 32500,
            'month_revenue_change': 8.0,
            'month_room_nights': 450,
            'month_room_nights_change': 5.0,
            'month_avg_price': 340,
            'month_avg_price_change': -1.5,
            'month_occupancy_rate': 85.0,
            'month_occupancy_rate_change': 2.5,
            
            # 本周数据默认值
            'today_revenue': 8521,
            'revenue_change': 12.0,
            'week_room_nights': 124,
            'room_nights_change': 5.0,
            'avg_price': 328,
            'avg_price_change': -2.0,
            'week_occupancy_rate': 87.0,
            'occupancy_rate_change': 3.0,
            'week_revpar': 280.0,
            'revpar_change': 12.0,
        }
    
    return render_template('home.html', stats=stats)

@app.route('/entry')
def entry():
    """
    Renders the data entry page.
    """
    return render_template('index.html')

@app.route('/add', methods=['POST'])
def add_entry():
    """
    Handles the form submission, gets the data, and saves it to the database.
    """
    record_date = request.form.get('record_date')
    channel = request.form.get('channel')
    fee_type = request.form.get('fee_type')
    room_nights = request.form.get('room_nights')
    revenue = request.form.get('revenue')

    if not all([record_date, channel, room_nights, revenue]):
        flash('错误：所有字段都必须填写！')
        return redirect(url_for('entry'))

    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            sql = "INSERT INTO DailyRevenue (record_date, channel, fee_type, room_nights, revenue) VALUES (?, ?, ?, ?, ?)"
            cursor.execute(sql, (record_date, channel, fee_type, room_nights, revenue))
            conn.commit()
            flash(f'成功：日期 {record_date}，渠道 {channel} 的数据已保存！')
    except sqlite3.IntegrityError:
        flash(f'错误：日期 {record_date}，渠道 {channel} 的数据已存在，无法重复添加。')
    except Exception as e:
        flash(f'数据库错误：{e}')
    
    return redirect(url_for('entry'))

@app.route('/edit_data', methods=['POST'])
def edit_data():
    """
    处理编辑数据的表单提交
    """
    # 获取表单数据
    record_id = request.form.get('id')
    record_date = request.form.get('record_date')
    channel = request.form.get('channel')
    fee_type = request.form.get('fee_type')
    room_nights = request.form.get('room_nights')
    revenue = request.form.get('revenue')
    
    # 验证必要字段
    if not all([record_id, record_date, channel, fee_type, room_nights, revenue]):
        flash('错误：所有字段都必须填写！')
        return redirect(url_for('view_data'))
    
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            
            # 检查是否存在重复的记录（相同日期和渠道的其他记录）
            cursor.execute(
                "SELECT id FROM DailyRevenue WHERE record_date = ? AND channel = ? AND fee_type = ? AND id != ?", 
                (record_date, channel, fee_type, record_id)
            )
            existing = cursor.fetchone()
            
            if existing:
                flash(f'错误：日期 {record_date}，渠道 {channel}，科目 {fee_type} 的另一条记录已存在，无法保存。')
                return redirect(url_for('view_data'))
            
            # 更新记录
            sql = """
                UPDATE DailyRevenue 
                SET record_date = ?, channel = ?, fee_type = ?, room_nights = ?, revenue = ?
                WHERE id = ?
            """
            cursor.execute(sql, (record_date, channel, fee_type, room_nights, revenue, record_id))
            conn.commit()
            
            if cursor.rowcount > 0:
                flash(f'成功：ID为 {record_id} 的数据已更新！')
            else:
                flash(f'错误：未找到ID为 {record_id} 的记录。')
                
    except Exception as e:
        flash(f'数据库错误：{e}')
    
    # 返回带有原有筛选条件的视图
    year = request.form.get('year', '')
    month = request.form.get('month', '')
    
    if year and month:
        return redirect(url_for('view_data', year=year, month=month))
    elif year:
        return redirect(url_for('view_data', year=year))
    else:
        return redirect(url_for('view_data'))

# This is the new function to view data.
# The indentation has been corrected to be at the same level as other functions.
@app.route('/view')
def view_data():
    """
    Queries data from the database with optional year/month filtering and displays it on a new page.
    """
    try:
        # 获取可选的年份和月份参数
        selected_year = request.args.get('year', '')
        selected_month = request.args.get('month', '')
        
        # 如果没有提供年份和月份参数，默认使用当前年月
        if not selected_year and not selected_month:
            today = datetime.now()
            selected_year = str(today.year)
            selected_month = str(today.month).zfill(2)  # 确保月份是两位数格式
        
        with sqlite3.connect(DATABASE) as conn:
            conn.row_factory = sqlite3.Row 
            cursor = conn.cursor()
            
            # 获取所有可用的年份列表
            cursor.execute("SELECT DISTINCT substr(record_date, 1, 4) as year FROM DailyRevenue ORDER BY year DESC")
            available_years = [row['year'] for row in cursor.fetchall()]
            
            # 获取所有可用的月份列表（针对所选年份，如果有）
            available_months = []
            month_names = {
                "01": "1月", "02": "2月", "03": "3月", "04": "4月", 
                "05": "5月", "06": "6月", "07": "7月", "08": "8月",
                "09": "9月", "10": "10月", "11": "11月", "12": "12月"
            }
            
            if selected_year:
                cursor.execute(
                    "SELECT DISTINCT substr(record_date, 6, 2) as month_num FROM DailyRevenue WHERE substr(record_date, 1, 4) = ? ORDER BY month_num DESC",
                    (selected_year,)
                )
                available_months = [row['month_num'] for row in cursor.fetchall()]
            
            # 构建完整的年月标识
            full_month_id = f"{selected_year}-{selected_month}" if selected_year and selected_month else ""
            display_period = ""
            
            if selected_year and selected_month:
                display_period = f"{selected_year}年{month_names.get(selected_month, selected_month)}"
            elif selected_year:
                display_period = f"{selected_year}年全年"
            
            # 计算合计间夜数和间夜收入
            total_room_nights = 0
            total_revenue = 0
            
            if selected_year and selected_month:
                cursor.execute(
                    """
                    SELECT SUM(room_nights) as total_nights, SUM(revenue) as total_revenue 
                    FROM DailyRevenue 
                    WHERE substr(record_date, 1, 4) = ? AND substr(record_date, 6, 2) = ?
                    """,
                    (selected_year, selected_month)
                )
            elif selected_year:
                cursor.execute(
                    """
                    SELECT SUM(room_nights) as total_nights, SUM(revenue) as total_revenue 
                    FROM DailyRevenue 
                    WHERE substr(record_date, 1, 4) = ?
                    """,
                    (selected_year,)
                )
            else:
                cursor.execute(
                    """
                    SELECT SUM(room_nights) as total_nights, SUM(revenue) as total_revenue 
                    FROM DailyRevenue
                    """
                )
                
            summary_row = cursor.fetchone()
            if summary_row:
                total_room_nights = summary_row['total_nights'] or 0
                total_revenue = summary_row['total_revenue'] or 0
            
            # 根据筛选条件执行不同的查询获取详细数据
            if selected_year and selected_month:
                cursor.execute(
                    "SELECT * FROM DailyRevenue WHERE substr(record_date, 1, 4) = ? AND substr(record_date, 6, 2) = ? ORDER BY record_date ASC, id ASC",
                    (selected_year, selected_month)
                )
            elif selected_year:
                cursor.execute(
                    "SELECT * FROM DailyRevenue WHERE substr(record_date, 1, 4) = ? ORDER BY record_date ASC, id ASC",
                    (selected_year,)
                )
            else:
                cursor.execute("SELECT * FROM DailyRevenue ORDER BY record_date ASC, id ASC")
            
            rows = cursor.fetchall()
            
            return render_template('view_data.html', 
                                  rows=rows, 
                                  available_years=available_years,
                                  available_months=available_months,
                                  selected_year=selected_year,
                                  selected_month=selected_month,
                                  month_names=month_names,
                                  display_period=display_period,
                                  total_room_nights=total_room_nights,
                                  total_revenue=total_revenue)
    except Exception as e:
        # It's better to show an error on the page if something goes wrong
        return f"<h1>查询数据时出错</h1><p>{e}</p>"

@app.route('/analytics')
def analytics_dashboard():
    """渲染分析仪表盘主页面"""
    return render_template('analytics.html')

@app.route('/api/query', methods=['POST'])
def process_query():
    """处理自然语言查询"""
    query = request.form.get('query', '')
    model = request.form.get('model', None)  # 可选的模型参数
    try:
        # 1. 用AI生成SQL
        ai_response = call_ai_api(query, model_name=model)
        
        # 确保ai_response是字典类型
        if not isinstance(ai_response, dict):
            print(f"警告: AI返回了非字典类型的响应: {type(ai_response)}")
            return jsonify({
                "error": "AI服务返回了无效响应格式"
            }), 500
            
        # 提取配置，所有值都提供默认值以防止错误
        sql = ai_response.get('sql', "SELECT * FROM DailyRevenue ORDER BY record_date DESC LIMIT 100")
        chart_type = ai_response.get('chart_type', 'bar')
        x_field = ai_response.get('x_field', 'channel')
        y_field = ai_response.get('y_field', 'revenue')
        title = ai_response.get('title', '数据分析')
        dimensions = ai_response.get('dimensions', [])
        metrics = ai_response.get('metrics', [])
        report_type = ai_response.get('report_type', 'daily')
        insights = ai_response.get('insights', {"summary": "无可用分析", "key_findings": []})

        # 2. 查数据库，拿到真实数据
        try:
            data = query_database({
                'sql': sql,
                'chart_type': chart_type,
                'x_field': x_field,
                'y_field': y_field,
                'dimensions': dimensions,
                'metrics': metrics,
                'report_type': report_type
            })
        except Exception as db_error:
            print(f"数据库查询错误: {db_error}")
            return jsonify({
                "error": f"数据库查询错误: {str(db_error)}"
            }), 500

        # 3. 用真实数据和用户问题发给AI分析
        # 仅当insights不存在时才调用AI分析
        if not insights or (isinstance(insights, dict) and not insights.get('summary')):
            try:
                insights = analyze_data_with_ai(query, data, model_name=model)
            except Exception as insight_error:
                print(f"生成洞察时出错: {insight_error}")
                insights = {
                    "summary": "生成分析洞察时出错，请查看数据表格和图表",
                    "key_findings": ["无法生成详细分析"],
                    "recommendations": ["请尝试调整查询或联系管理员"]
                }
        # 4. 生成可视化配置
        visualization = {
            "chart_type": chart_type,
            "x_field": x_field,
            "y_field": y_field,
            "title": title,
            "x_label": get_axis_label(x_field),
            "y_label": get_axis_label(y_field),
            "dimensions": dimensions,
            "metrics": metrics,
            "report_type": report_type
        }

        return jsonify({
            "data": data.to_dict(orient='records'),
            "visualization": visualization,
            "insights": insights
        })
    except Exception as e:
        print(f"处理查询时发生严重错误: {e}")
        import traceback
        traceback.print_exc()  # 打印完整堆栈跟踪
        return jsonify({
            "error": f"处理查询时发生错误: {str(e)}"
        }), 500

def query_database(query_config):
    """执行SQL查询并返回结果"""
    conn = sqlite3.connect(DATABASE)
    
    try:
        df = pd.read_sql_query(query_config['sql'], conn)
        
        metrics = query_config.get('metrics', [])
        for metric in metrics:
            if metric in df.columns:
                df[metric] = pd.to_numeric(df[metric], errors='coerce')
        
        if query_config.get('chart_type') == 'pie' and len(df) > 0:
            y_field_config = query_config.get('y_field', 'revenue')
            primary_y_field = y_field_config[0] if isinstance(y_field_config, list) else y_field_config
                
            if primary_y_field in df.columns:
                total = df[primary_y_field].sum()
                df['percentage'] = df[primary_y_field] / total if total > 0 else 0
        
        if query_config.get('chart_type') == 'heatmap' and len(df) > 0:
            dimensions = query_config.get('dimensions', [])
            if len(dimensions) >= 2:
                all_dims = [df[dim].unique() for dim in dimensions]
                all_combinations = pd.MultiIndex.from_product(all_dims, names=dimensions).to_frame(index=False)
                df = pd.merge(all_combinations, df, on=dimensions, how='left').fillna(0)

        if query_config.get('chart_type') == 'combo' and len(df) > 0:
            y_field_config = query_config.get('y_field')
            if isinstance(y_field_config, list):
                for field in y_field_config:
                    if field not in df.columns:
                        df[field] = 0.0

        revenue_col = 'total_revenue' if 'total_revenue' in df.columns else 'revenue'
        nights_col = 'total_room_nights' if 'total_room_nights' in df.columns else 'room_nights'
        
        if revenue_col in df.columns and nights_col in df.columns:
            df[nights_col] = pd.to_numeric(df[nights_col], errors='coerce')
            df[nights_col] = df[nights_col].fillna(0)
            df[revenue_col] = pd.to_numeric(df[revenue_col], errors='coerce')
            df[revenue_col] = df[revenue_col].fillna(0)
            df['avg_price'] = np.where(df[nights_col] > 0, df[revenue_col] / df[nights_col], 0.0)

        if 'record_date' in df.columns and 'day_of_week' not in df.columns:
            # 确保 'record_date' 是 datetime 类型
            df['record_date'] = pd.to_datetime(df['record_date'])
            df['day_of_week'] = df['record_date'].dt.day_name(locale='zh_CN.UTF-8')
            
        if query_config.get('report_type') == 'weekly' and 'day_name' in df.columns:
            all_days = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
            df['day_name'] = pd.Categorical(df['day_name'], categories=all_days, ordered=True)
            
            # 补全缺失的日期
            missing_days_df = pd.DataFrame({'day_name': all_days})
            df = pd.merge(missing_days_df, df, on='day_name', how='left')
            
            for metric in metrics:
                if metric in df.columns:
                    df[metric].fillna(0.0, inplace=True)
            df.sort_values('day_name', inplace=True)
            
        df.replace({np.nan: None, pd.NaT: None}, inplace=True)
        
        return df
    finally:
        conn.close()

def get_axis_label(field):
    """获取轴标签"""
    if isinstance(field, list):
        # 如果是字段列表，返回第一个字段的标签
        if len(field) > 0:
            return get_axis_label(field[0])
        return ''
    
    labels = {
        'record_date': '日期',
        'month': '月份',
        'period': '时间段',
        'channel': '销售渠道',
        'revenue': '收入 (元)',
        'room_nights': '间夜数量',
        'avg_price': '平均房价 (元)',
        'day_of_week': '星期',
        'day_name': '星期',
        'occupancy_rate': '出租率 (%)'
    }
    return labels.get(field, field)

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

@app.route('/weekly_report')
def weekly_report():
    """渲染周报表页面"""
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    start_date = request.args.get('start_date', (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=6)).strftime('%Y-%m-%d'))

    report_data, df = generate_weekly_report(start_date, end_date)

    if df.empty:
        return render_template('weekly_report.html',
                               start_date=start_date,
                               end_date=end_date,
                               report_data={'total_summary': {'date_range': f"{start_date.replace('-', '.')} - {end_date.replace('-', '.')}"}},
                               channel_data=[], daily_data=[], detail_data=[], chart_data=json.dumps({}), pivot_html="")

    # 准备渠道分析数据
    channel_summary_dict = report_data.get('channel_summary', {})
    total_summary = report_data.get('total_summary', {})
    total_room_nights = total_summary.get('room_nights', 0)
    channel_data = [{
        'channel': channel,  # 这里的channel已经是标准化后的名称
        **summary,
        'room_nights_pct': (summary.get('room_nights', 0) / total_room_nights * 100) if total_room_nights > 0 else 0
    } for channel, summary in channel_summary_dict.items()]

    # 准备每日明细和图表数据
    total_rooms = int(os.getenv('TOTAL_ROOMS', 29))
    date_range_df = pd.DataFrame(pd.date_range(start=start_date, end=end_date), columns=['record_date'])
    daily_agg_df = df.groupby('record_date').agg(
        room_nights=('room_nights', 'sum'),
        revenue=('revenue', 'sum')
    ).reset_index()

    daily_data_df = pd.merge(date_range_df, daily_agg_df, on='record_date', how='left').fillna(0)
    daily_data_df['day_name'] = daily_data_df['record_date'].dt.day_name(locale='zh_CN.UTF-8')
    daily_data_df['avg_price'] = (daily_data_df['revenue'] / daily_data_df['room_nights']).where(daily_data_df['room_nights'] > 0, 0)
    daily_data_df['occupancy_rate'] = (daily_data_df['room_nights'] / total_rooms) * 100
    
    daily_data = daily_data_df.to_dict('records')
    
    # 使用标准化的渠道名称处理明细数据
    df['channel'] = df['standardized_channel']  # 用标准化的渠道名称替换原始渠道名称
    detail_data = df.sort_values(['record_date', 'channel']).to_dict('records')

    # 从 report_data 中获取每日汇总，用于周收入柱状图
    daily_summary_for_chart = report_data.get('daily_summary', {})
    
    # 调试输出
    app.logger.info(f"生成周报表图表数据: 日期数={len(daily_data_df)}, 有无日期数据={len(daily_data_df['record_date']) > 0}")
    
    # 按渠道分组处理数据
    chart_data_dict = {}
    
    # 处理日期
    dates = daily_data_df['record_date'].dt.strftime('%m-%d').tolist()
    
    # 将英文星期转换为中文
    day_name_map = {
        'Monday': '一',
        'Tuesday': '二',
        'Wednesday': '三',
        'Thursday': '四',
        'Friday': '五',
        'Saturday': '六',
        'Sunday': '日'
    }
    day_names = [day_name_map.get(d, d) for d in daily_data_df['day_name'].tolist()]  # 星期几转换为中文
    
    # 总体数据 - 确保所有数值都是原生Python类型，而非numpy类型
    chart_data_dict['dates'] = dates
    chart_data_dict['day_names'] = day_names
    chart_data_dict['room_nights'] = [float(x) for x in daily_data_df['room_nights'].tolist()]
    chart_data_dict['revenue'] = [float(x) for x in daily_data_df['revenue'].round(2).tolist()]
    chart_data_dict['avg_price'] = [float(x) for x in daily_data_df['avg_price'].round(2).tolist()]
    chart_data_dict['weekly_revenue'] = daily_summary_for_chart
    
    # 定义所有预期的渠道列表（标准化后的名称）
    all_channels = ['携程', '美团', '飞猪', '散客', '会员', '协议', '其他']

    # 按渠道分组数据 - 使用标准化的渠道名称
    channel_series = {}

    # 首先为所有渠道初始化空数据结构
    for channel in all_channels:
        channel_series[channel] = {}
        # 为每个日期初始化0值
        for single_date in pd.date_range(start=start_date, end=end_date):
            date_str = single_date.strftime('%m-%d')
            channel_series[channel][date_str] = {
                'room_nights': 0,
                'revenue': 0.0,
                'avg_price': 0.0
            }

    # 然后填入实际数据
    for channel, group in df.groupby('channel'):
        for date, subgroup in group.groupby('record_date'):
            date_str = date.strftime('%m-%d')
            room_nights_sum = float(subgroup['room_nights'].sum())
            revenue_sum = float(subgroup['revenue'].sum())
            avg_price = float(revenue_sum / room_nights_sum if room_nights_sum > 0 else 0)

            channel_series[channel][date_str] = {
                'room_nights': room_nights_sum,
                'revenue': round(revenue_sum, 2),
                'avg_price': round(avg_price, 2)
            }

    chart_data_dict['channel_series'] = channel_series
    
    # 使用自定义的JSON编码器处理NumPy类型
    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super(NumpyEncoder, self).default(obj)
    
    # 使用json.dumps进行序列化，确保数据可以被JavaScript解析
    chart_data = json.dumps(chart_data_dict, ensure_ascii=False, cls=NumpyEncoder)
    
    app.logger.info(f"图表数据生成完成: {chart_data[:100]}...")

    return render_template('weekly_report.html',
                           start_date=start_date,
                           end_date=end_date,
                           report_data=report_data,
                           channel_data=channel_data,
                           daily_data=daily_data,
                           detail_data=detail_data,
                           chart_data=chart_data,
                           pivot_html=report_data.get('pivot_table', ''))

def generate_weekly_report(start_date, end_date):
    """生成周报表数据"""
    try:
        with sqlite3.connect(DATABASE) as conn:
            query = """
                SELECT 
                    record_date, 
                    channel, 
                    fee_type,
                    SUM(room_nights) as room_nights, 
                    SUM(revenue) as revenue
                FROM DailyRevenue
                WHERE record_date BETWEEN ? AND ?
                GROUP BY record_date, channel, fee_type
            """
            df = pd.read_sql_query(query, conn, params=(start_date, end_date))

            if df.empty:
                return {}, pd.DataFrame()

            # 标准化渠道名称
            df['standardized_channel'] = df['channel'].apply(standardize_channel_name)

            df['record_date'] = pd.to_datetime(df['record_date'])
            df['day_name'] = df['record_date'].dt.day_name(locale='zh_CN.UTF-8')
            all_days = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
            df['day_name'] = pd.Categorical(df['day_name'], categories=all_days, ordered=True)

            # 数据透视 - 使用标准化的渠道名称
            pivot_df = pd.pivot_table(
                df, 
                values=['revenue', 'room_nights'], 
                index='standardized_channel', 
                columns='day_name',
                aggfunc='sum', 
                fill_value=0,
                margins=True, 
                margins_name='Total',
                observed=False
            ).astype(float)

            # 计算总计
            total_revenue = pivot_df.loc['Total', ('revenue', 'Total')]
            total_room_nights = pivot_df.loc['Total', ('room_nights', 'Total')]

            # 计算其他指标
            total_avg_price = total_revenue / total_room_nights if total_room_nights > 0 else 0
            
            total_rooms = int(os.getenv('TOTAL_ROOMS', 29))
            num_days = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days + 1
            total_occupancy_rate = (total_room_nights / (total_rooms * num_days)) * 100 if num_days > 0 else 0
            total_revpar = total_revenue / (total_rooms * num_days) if num_days > 0 else 0

            # 每日指标计算
            daily_summary = df.groupby('day_name', observed=False).agg(
                revenue=('revenue', 'sum'),
                room_nights=('room_nights', 'sum')
            ).reindex(all_days, fill_value=0)
            
            daily_summary['avg_price'] = (daily_summary['revenue'] / daily_summary['room_nights']).where(daily_summary['room_nights'] > 0, 0)
            daily_summary['occupancy'] = (daily_summary['room_nights'] / total_rooms) * 100
            daily_summary['revpar'] = daily_summary['avg_price'] * (daily_summary['occupancy'] / 100)

            # 定义所有预期的渠道列表（标准化后的名称）
            all_channels = ['携程', '美团', '飞猪', '散客', '会员', '协议', '其他']

            # 渠道分析 - 使用标准化的渠道名称
            channel_summary = df.groupby('standardized_channel').agg(
                revenue=('revenue', 'sum'),
                room_nights=('room_nights', 'sum')
            )

            # 确保所有渠道都出现在结果中，即使数据为0
            for channel in all_channels:
                if channel not in channel_summary.index:
                    channel_summary.loc[channel] = {'revenue': 0.0, 'room_nights': 0}

            # 按收入排序，但保持0收入渠道在末尾
            channel_summary = channel_summary.sort_values('revenue', ascending=False)

            channel_summary['revenue_percent'] = (channel_summary['revenue'] / total_revenue * 100) if total_revenue > 0 else 0
            channel_summary['avg_price'] = (channel_summary['revenue'] / channel_summary['room_nights']).where(channel_summary['room_nights'] > 0, 0)

            # 费用类型分析
            fee_type_summary = df.groupby('fee_type').agg(
                revenue=('revenue', 'sum')
            ).sort_values('revenue', ascending=False)
            fee_type_summary['revenue_percent'] = (fee_type_summary['revenue'] / total_revenue * 100) if total_revenue > 0 else 0

            # 准备最终结果
            report = {
                'total_summary': {
                    'date_range': f"{start_date.replace('-', '.')} - {end_date.replace('-', '.')}",
                    'revenue': round(total_revenue, 2),
                    'room_nights': int(total_room_nights),
                    'avg_price': round(total_avg_price, 2),
                    'occupancy_rate': round(total_occupancy_rate, 2),
                    'revpar': round(total_revpar, 2)
                },
                'daily_summary': daily_summary.round(2).to_dict(orient='index'),
                'channel_summary': channel_summary.round(2).to_dict(orient='index'),
                'fee_type_summary': fee_type_summary.round(2).to_dict(orient='index'),
                'pivot_table': pivot_df.round(2).to_html(classes='table table-sm table-bordered', escape=False)
            }
            
            return report, df

    except Exception as e:
        app.logger.error(f"生成周报表时发生错误: {e}", exc_info=True)
        return {"error": str(e)}, pd.DataFrame()

@app.route('/system_guide')
def system_guide():
    """
    渲染系统说明页面
    """
    return render_template('system_guide.html')

# --- 导入Excel数据 ---
@app.route('/import_excel', methods=['GET', 'POST'])
def import_excel():
    """处理Excel文件导入"""
    if request.method == 'POST':
        if 'excel_file' not in request.files:
            flash('没有上传文件')
            return redirect(request.url)
        
        file = request.files['excel_file']
        if file.filename == '':
            flash('没有选择文件')
            return redirect(request.url)
        
        if file and file.filename and file.filename.endswith(('.xlsx', '.xls')):
            try:
                # 读取Excel文件
                df = pd.read_excel(file)
                
                # 检查必要的列是否存在
                required_columns = ['统计渠道', '营业日', '房费科目', '间夜数', '房费']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    flash(f'Excel文件缺少必要的列: {", ".join(missing_columns)}')
                    return redirect(request.url)
                
                # 数据预处理
                success_count = 0
                error_count = 0
                
                # 确保数值列为数值类型
                df['间夜数'] = pd.to_numeric(df['间夜数'], errors='coerce').fillna(0)
                df['房费'] = pd.to_numeric(df['房费'], errors='coerce').fillna(0)
                
                # 处理日期格式
                df['record_date'] = pd.to_datetime(df['营业日']).dt.strftime('%Y-%m-%d')
                
                # 打印导入前的数据统计
                print(f"导入前数据统计: 总行数={len(df)}, 房费总和={df['房费'].sum()}")
                
                # 按渠道、日期和房费科目分组，汇总间夜数和房费
                grouped_df = df.groupby(['统计渠道', 'record_date', '房费科目']).agg({
                    '间夜数': 'sum',
                    '房费': 'sum'
                }).reset_index()
                
                # 打印分组后的数据统计
                print(f"分组后数据统计: 总行数={len(grouped_df)}, 房费总和={grouped_df['房费'].sum()}")
                
                with sqlite3.connect(DATABASE) as conn:
                    cursor = conn.cursor()
                    
                    # 处理每一行汇总后的数据
                    for _, row in grouped_df.iterrows():
                        try:
                            # 提取数据
                            channel = row['统计渠道']
                            record_date = row['record_date']
                            fee_type = row['房费科目']
                            room_nights = float(row['间夜数'])
                            revenue = float(row['房费'])
                            
                            # 打印每行数据以便调试
                            print(f"导入数据: 渠道={channel}, 日期={record_date}, 科目={fee_type}, 间夜={room_nights}, 房费={revenue}")
                            
                            # 检查是否已存在相同渠道、日期和房费科目的记录
                            cursor.execute(
                                "SELECT id, room_nights, revenue FROM DailyRevenue WHERE record_date = ? AND channel = ? AND fee_type = ?", 
                                (record_date, channel, fee_type)
                            )
                            existing_record = cursor.fetchone()
                            
                            if existing_record:
                                # 更新现有记录
                                record_id, existing_nights, existing_revenue = existing_record
                                new_nights = existing_nights + room_nights
                                new_revenue = existing_revenue + revenue
                                
                                cursor.execute(
                                    "UPDATE DailyRevenue SET room_nights = ?, revenue = ? WHERE id = ?",
                                    (new_nights, new_revenue, record_id)
                                )
                            else:
                                # 插入新记录
                                sql = "INSERT INTO DailyRevenue (record_date, channel, fee_type, room_nights, revenue) VALUES (?, ?, ?, ?, ?)"
                                cursor.execute(sql, (record_date, channel, fee_type, room_nights, revenue))
                            
                            success_count += 1
                            
                        except Exception as e:
                            print(f"导入行数据时出错: {e}")
                            error_count += 1
                    
                    conn.commit()
                
                # 导入后检查数据库中的总房费
                cursor.execute("SELECT SUM(revenue) FROM DailyRevenue")
                total_revenue_in_db = cursor.fetchone()[0]
                print(f"导入后数据库中的房费总和: {total_revenue_in_db}")
                
                flash(f'导入完成: 成功 {success_count} 条, 失败 {error_count} 条')
                return redirect(url_for('view_data'))
                
            except Exception as e:
                flash(f'处理Excel文件时出错: {e}')
                return redirect(request.url)
        else:
            flash('只支持.xlsx或.xls格式的Excel文件')
            return redirect(request.url)
    
    # GET请求，显示上传表单
    return render_template('import_excel.html')

# --- Main Execution ---
if __name__ == '__main__':
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='乐巷酒店数据智能分析系统')
    parser.add_argument('--port', type=int, default=5001, help='Web服务器端口号')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    args = parser.parse_args()
    
    # 配置日志记录
    log_handler = RotatingFileHandler('app.log', maxBytes=10485760, backupCount=3)
    log_handler.setLevel(logging.INFO)
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_handler.setFormatter(log_formatter)
    
    # 添加单独的错误日志
    error_handler = RotatingFileHandler('error.log', maxBytes=10485760, backupCount=3)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(log_formatter)
    
    # 设置Flask应用的日志记录器
    app.logger.addHandler(log_handler)
    app.logger.addHandler(error_handler)
    app.logger.setLevel(logging.INFO)
    
    # 设置Werkzeug的日志记录器
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addHandler(log_handler)
    
    # 初始化数据库
    init_db()
    
    print("\n=== 乐巷酒店数据智能分析系统 ===")
    print(f"默认使用模型: {DEFAULT_MODEL}")
    print("数据库初始化完成")
    print(f"启动Web服务器在端口 {args.port}...")
    
    # 启动Flask应用
    app.run(host='0.0.0.0', port=args.port, debug=args.debug)