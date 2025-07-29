import sqlite3
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify, session, send_file
from ai_service import call_ai_api, analyze_data_with_ai, DEFAULT_MODEL
import argparse
import logging
import shutil
import hashlib
from logging.handlers import RotatingFileHandler

try:
    from dotenv import load_dotenv
    # 加载 .env 文件中的环境变量
    load_dotenv()
    print("已加载.env文件")
except ImportError:
    print("未安装python-dotenv，将直接使用环境变量")

# --- App Configuration ---
app = Flask(__name__)
# This secret key is needed to show flashed messages
app.config['SECRET_KEY'] = 'a_very_secret_key_that_should_be_changed' 

# --- Database Configuration ---
# Get the absolute path of the directory where the script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Define the path to the database file
DATABASE = os.path.join(BASE_DIR, 'hotel_revenue.db')

# --- 配置日志记录 ---
# 确保日志目录存在
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# 配置日志处理器
log_handler = RotatingFileHandler(os.path.join(LOG_DIR, 'app.log'), maxBytes=10485760, backupCount=5)
log_handler.setLevel(logging.INFO)
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler.setFormatter(log_formatter)

# 添加单独的错误日志
error_handler = RotatingFileHandler(os.path.join(LOG_DIR, 'error.log'), maxBytes=10485760, backupCount=5)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(log_formatter)

# 设置Flask应用的日志记录器
app.logger.addHandler(log_handler)
app.logger.addHandler(error_handler)
app.logger.setLevel(logging.INFO)

# 设置Werkzeug的日志记录器
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addHandler(log_handler)

# 记录应用启动信息
app.logger.info("=== 乐巷酒店数据智能分析系统启动 ===")

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

            # --- 上周数据计算（用于显示上周统计，对比上上周） ---
            # 上上周的日期范围
            two_weeks_ago_start = (today - timedelta(days=today.weekday() + 14)).strftime('%Y-%m-%d')
            two_weeks_ago_end = (today - timedelta(days=today.weekday() + 8)).strftime('%Y-%m-%d')

            # 1. 上周收入
            # last_week_revenue 已经在上面计算过了

            # 获取上上周收入，用于计算同比
            cursor.execute("SELECT SUM(revenue) FROM DailyRevenue WHERE record_date >= ? AND record_date <= ?",
                          (two_weeks_ago_start, two_weeks_ago_end))
            two_weeks_ago_revenue = cursor.fetchone()[0] or 0

            # 计算上周收入同比变化（vs 上上周）
            last_week_revenue_change = 0
            if two_weeks_ago_revenue > 0:
                last_week_revenue_change = ((last_week_revenue - two_weeks_ago_revenue) / two_weeks_ago_revenue) * 100

            # 2. 上周间夜数
            # last_week_room_nights 已经在上面计算过了

            # 获取上上周间夜数，用于计算同比
            cursor.execute("SELECT SUM(room_nights) FROM DailyRevenue WHERE record_date >= ? AND record_date <= ?",
                          (two_weeks_ago_start, two_weeks_ago_end))
            two_weeks_ago_room_nights = cursor.fetchone()[0] or 0

            # 计算上周间夜同比变化（vs 上上周）
            last_week_room_nights_change = 0
            if two_weeks_ago_room_nights > 0:
                last_week_room_nights_change = ((last_week_room_nights - two_weeks_ago_room_nights) / two_weeks_ago_room_nights) * 100

            # 3. 上周平均房价
            # last_week_avg_price 已经在上面计算过了

            # 获取上上周平均房价，用于计算同比
            cursor.execute("""
                SELECT SUM(revenue) / SUM(room_nights)
                FROM DailyRevenue
                WHERE record_date >= ? AND record_date <= ? AND room_nights > 0
            """, (two_weeks_ago_start, two_weeks_ago_end))
            two_weeks_ago_avg_price = cursor.fetchone()[0] or 0

            # 计算上周平均房价同比变化（vs 上上周）
            last_week_avg_price_change = 0
            if two_weeks_ago_avg_price > 0:
                last_week_avg_price_change = ((last_week_avg_price - two_weeks_ago_avg_price) / two_weeks_ago_avg_price) * 100

            # 4. 上周入住率
            # last_week_occupancy_rate 已经在上面计算过了

            # 获取上上周入住率，用于计算同比
            cursor.execute("""
                SELECT SUM(room_nights) * 100.0 / (? * 7)
                FROM DailyRevenue
                WHERE record_date >= ? AND record_date <= ?
            """, (total_rooms, two_weeks_ago_start, two_weeks_ago_end))
            two_weeks_ago_occupancy_rate = cursor.fetchone()[0] or 0

            # 计算上周入住率同比变化（vs 上上周）
            last_week_occupancy_rate_change = 0
            if two_weeks_ago_occupancy_rate > 0:
                last_week_occupancy_rate_change = ((last_week_occupancy_rate - two_weeks_ago_occupancy_rate) / two_weeks_ago_occupancy_rate) * 100

            # 5. 计算上周 RevPAR
            # last_week_revpar 已经在上面计算过了
            two_weeks_ago_revpar = (two_weeks_ago_avg_price * two_weeks_ago_occupancy_rate) / 100 if two_weeks_ago_occupancy_rate > 0 else 0

            last_week_revpar_change = 0
            if two_weeks_ago_revpar > 0:
                last_week_revpar_change = ((last_week_revpar - two_weeks_ago_revpar) / two_weeks_ago_revpar) * 100

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
                
                # 上周数据
                'last_week_revenue': int(last_week_revenue),
                'last_week_revenue_change': round(last_week_revenue_change, 1),
                'last_week_room_nights': int(last_week_room_nights),
                'last_week_room_nights_change': round(last_week_room_nights_change, 1),
                'last_week_avg_price': round(last_week_avg_price, 2),
                'last_week_avg_price_change': round(last_week_avg_price_change, 1),
                'last_week_occupancy_rate': round(last_week_occupancy_rate, 2),
                'last_week_occupancy_rate_change': round(last_week_occupancy_rate_change, 1),
                'last_week_revpar': round(last_week_revpar, 2),
                'last_week_revpar_change': round(last_week_revpar_change, 1),

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
            'month_revpar': 57,
            'month_revpar_change': 31.3,

            # 上周数据默认值
            'last_week_revenue': 0,
            'last_week_revenue_change': -100.0,
            'last_week_room_nights': 0,
            'last_week_room_nights_change': -100.0,
            'last_week_avg_price': 0,
            'last_week_avg_price_change': -100.0,
            'last_week_occupancy_rate': 0,
            'last_week_occupancy_rate_change': -100.0,
            'last_week_revpar': 0,
            'last_week_revpar_change': -100.0,

            # 本周数据默认值
            'today_revenue': 0,
            'revenue_change': -100.0,
            'week_room_nights': 0,
            'room_nights_change': -100.0,
            'avg_price': 0,
            'avg_price_change': -100.0,
            'week_occupancy_rate': 0,
            'occupancy_rate_change': -100.0,
            'week_revpar': 0,
            'revpar_change': -100.0,
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
            # 使用英文区域设置，避免locale错误
            df['day_of_week'] = df['record_date'].dt.day_name()
            # 将英文星期几转换为中文
            day_name_map = {
                'Monday': '星期一',
                'Tuesday': '星期二',
                'Wednesday': '星期三',
                'Thursday': '星期四',
                'Friday': '星期五',
                'Saturday': '星期六',
                'Sunday': '星期日'
            }
            df['day_of_week'] = df['day_of_week'].map(day_name_map)
            
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
    elif channel in ['抖音来客', '抖音', '其他']:
        return '抖音来客'
    elif channel in ['散客', '门店']:
        return '散客'
    return channel

@app.route('/weekly_report')
def weekly_report():
    """渲染周报表页面"""
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    start_date = request.args.get('start_date', (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=6)).strftime('%Y-%m-%d'))

    report_data, df = generate_weekly_report(start_date, end_date)

    if df.empty:
        empty_total_summary = {
            'date_range': f"{start_date.replace('-', '.')} - {end_date.replace('-', '.')}",
            'total_revenue': 0.0,
            'room_revenue': 0.0,
            'hourly_revenue': 0.0,
            'room_nights': 0,
            'avg_price': 0.0,
            'occupancy_rate': 0.0
        }
        return render_template('weekly_report.html',
                               start_date=start_date,
                               end_date=end_date,
                               report_data={'total_summary': empty_total_summary},
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
    # 使用英文区域设置，避免locale错误
    daily_data_df['day_name'] = daily_data_df['record_date'].dt.day_name()
    # 将英文星期几转换为中文
    day_name_map = {
        'Monday': '星期一',
        'Tuesday': '星期二',
        'Wednesday': '星期三',
        'Thursday': '星期四',
        'Friday': '星期五',
        'Saturday': '星期六',
        'Sunday': '星期日'
    }
    daily_data_df['day_name'] = daily_data_df['day_name'].map(day_name_map)
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
    
    # 定义预期的渠道列表（标准化后的名称）
    expected_channels = ['携程', '美团', '飞猪', '抖音来客', '散客']  # , '会员', '协议'  # 暂时注释，以后可能会用

    # 获取实际存在的渠道
    actual_channels = set(df['channel'].unique()) if not df.empty else set()
    all_channels = list(actual_channels.union(set(expected_channels)))

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
            # 查询本周数据
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

            # 计算上周日期范围
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            days_diff = (end_dt - start_dt).days + 1

            last_week_end = start_dt - timedelta(days=1)
            last_week_start = last_week_end - timedelta(days=days_diff-1)

            last_week_start_str = last_week_start.strftime('%Y-%m-%d')
            last_week_end_str = last_week_end.strftime('%Y-%m-%d')

            # 查询上周数据
            df_last_week = pd.read_sql_query(query, conn, params=(last_week_start_str, last_week_end_str))

            if df.empty:
                # 返回空报表结构，保持与预期结构一致
                empty_report = {
                    "total_summary": {
                        "date_range": f"{start_date.replace('-', '.')} - {end_date.replace('-', '.')}",
                        "total_revenue": 0.0,
                        "room_revenue": 0.0,
                        "hourly_revenue": 0.0,
                        "room_nights": 0,
                        "avg_price": 0.0,
                        "occupancy_rate": 0.0,
                        "revpar": 0.0
                    },
                    "daily_summary": {},
                    "channel_summary": {},
                    "fee_type_summary": {},
                    "pivot_table": "<table></table>"
                }
                return empty_report, pd.DataFrame()

            # 标准化渠道名称
            df['standardized_channel'] = df['channel'].apply(standardize_channel_name)

            df['record_date'] = pd.to_datetime(df['record_date'])
            # 使用英文区域设置而非中文，避免区域设置问题
            df['day_name'] = df['record_date'].dt.day_name()
            
            # 将英文星期几映射为中文
            day_name_map = {
                'Monday': '星期一',
                'Tuesday': '星期二',
                'Wednesday': '星期三',
                'Thursday': '星期四',
                'Friday': '星期五',
                'Saturday': '星期六',
                'Sunday': '星期日'
            }
            df['day_name'] = df['day_name'].map(day_name_map)
            
            all_days = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
            df['day_name'] = pd.Categorical(df['day_name'], categories=all_days, ordered=True)

            # 数据透视 - 将星期作为列而不是行，使用标准化的渠道名称
            pivot_df = pd.pivot_table(
                df, 
                values=['revenue', 'room_nights'], 
                index='standardized_channel',  # 使用标准化的渠道名称作为行索引
                columns='day_name',  # 星期作为列
                aggfunc='sum', 
                fill_value=0,
                margins=True, 
                margins_name='合计',
                observed=False
            ).astype(float)

            # 定义预期的渠道列表（标准化后的名称）
            expected_channels = ['携程', '美团', '飞猪', '抖音来客', '散客']  # , '会员', '协议'  # 暂时注释，以后可能会用

            # 渠道分析 - 使用标准化的渠道名称，分别计算住宿收入和钟点房收入
            # 住宿收入：房费 + 手工输入房费 + 调整房费
            accommodation_df = df[df['fee_type'].isin(['房费', '手工输入房费', '调整房费'])]
            # 钟点房收入：加收全天
            hourly_df = df[df['fee_type'] == '加收全天']

            # 计算总计 - 分别计算不同类型的收入
            total_room_revenue = accommodation_df['revenue'].sum()  # 间夜房收入（不含钟点房）
            total_hourly_revenue = hourly_df['revenue'].sum()  # 钟点房收入
            total_accommodation_revenue = total_room_revenue + total_hourly_revenue  # 住宿费用总计（含钟点房）
            total_room_nights = accommodation_df['room_nights'].sum()  # 只计算住宿间夜数

            # 计算其他指标
            total_avg_price = total_room_revenue / total_room_nights if total_room_nights > 0 else 0  # 平均房价不含钟点房

            total_rooms = int(os.getenv('TOTAL_ROOMS', 29))
            num_days = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days + 1
            total_occupancy_rate = (total_room_nights / (total_rooms * num_days)) * 100 if num_days > 0 else 0
            total_revpar = total_accommodation_revenue / (total_rooms * num_days) if num_days > 0 else 0  # RevPAR用住宿费用总计

            # 每日指标计算 - 保持按星期分组，用于图表数据
            daily_summary = accommodation_df.groupby('day_name', observed=False).agg(
                revenue=('revenue', 'sum'),
                room_nights=('room_nights', 'sum')
            ).reindex(all_days, fill_value=0)

            daily_summary['avg_price'] = (daily_summary['revenue'] / daily_summary['room_nights']).where(daily_summary['room_nights'] > 0, 0)
            daily_summary['occupancy'] = (daily_summary['room_nights'] / total_rooms) * 100
            daily_summary['revpar'] = daily_summary['avg_price'] * (daily_summary['occupancy'] / 100)

            channel_summary = accommodation_df.groupby('standardized_channel').agg(
                room_revenue=('revenue', 'sum'),  # 间夜房收入
                room_nights=('room_nights', 'sum')
            )

            # 计算钟点房收入
            hourly_summary = hourly_df.groupby('standardized_channel').agg(
                hourly_revenue=('revenue', 'sum')
            )

            # 获取实际存在的渠道和预期渠道的并集
            actual_channels = set(channel_summary.index.tolist())
            all_channels = list(actual_channels.union(set(expected_channels)))

            # 确保所有渠道都出现在结果中，即使数据为0
            for channel in all_channels:
                if channel not in channel_summary.index:
                    channel_summary.loc[channel] = {'room_revenue': 0.0, 'room_nights': 0}
                if channel not in hourly_summary.index:
                    hourly_summary.loc[channel] = {'hourly_revenue': 0.0}

            # 合并钟点房收入到渠道汇总中
            channel_summary = channel_summary.join(hourly_summary, how='left')
            channel_summary['hourly_revenue'] = channel_summary['hourly_revenue'].fillna(0.0)

            # 计算住宿费用总计（间夜房收入 + 钟点房收入）
            channel_summary['total_revenue'] = channel_summary['room_revenue'] + channel_summary['hourly_revenue']

            # 按住宿费用总计排序，但保持0收入渠道在末尾
            channel_summary = channel_summary.sort_values('total_revenue', ascending=False)

            # 计算各种占比和平均值
            channel_summary['revenue_percent'] = (channel_summary['room_revenue'] / total_room_revenue * 100) if total_room_revenue > 0 else 0  # 间夜房收入占比
            channel_summary['avg_price'] = (channel_summary['room_revenue'] / channel_summary['room_nights']).where(channel_summary['room_nights'] > 0, 0)  # 平均房价不含钟点房

            # 处理上周数据进行对比分析
            channel_comparison = {}

            # 初始化上周数据汇总
            last_week_channel_summary = pd.DataFrame(columns=['room_revenue', 'room_nights'])

            if not df_last_week.empty:
                # 标准化上周数据的渠道名称
                df_last_week['standardized_channel'] = df_last_week['channel'].apply(standardize_channel_name)

                # 分离上周的住宿收入和钟点房收入
                last_week_accommodation_df = df_last_week[df_last_week['fee_type'].isin(['房费', '手工输入房费', '调整房费'])]

                # 上周渠道分析
                last_week_channel_summary = last_week_accommodation_df.groupby('standardized_channel').agg(
                    room_revenue=('revenue', 'sum'),
                    room_nights=('room_nights', 'sum')
                )

            # 确保所有渠道都出现在上周数据中
            for channel in all_channels:
                if channel not in last_week_channel_summary.index:
                    last_week_channel_summary.loc[channel] = {'room_revenue': 0.0, 'room_nights': 0}

            # 计算对比数据（无论是否有上周数据都要计算）
            for channel in all_channels:
                current_revenue = channel_summary.loc[channel, 'room_revenue'] if channel in channel_summary.index else 0
                current_room_nights = channel_summary.loc[channel, 'room_nights'] if channel in channel_summary.index else 0

                last_revenue = last_week_channel_summary.loc[channel, 'room_revenue'] if channel in last_week_channel_summary.index else 0
                last_room_nights = last_week_channel_summary.loc[channel, 'room_nights'] if channel in last_week_channel_summary.index else 0

                # 计算变化
                revenue_change = current_revenue - last_revenue
                room_nights_change = current_room_nights - last_room_nights

                # 计算变化率
                revenue_change_rate = (revenue_change / last_revenue * 100) if last_revenue > 0 else 0
                room_nights_change_rate = (room_nights_change / last_room_nights * 100) if last_room_nights > 0 else 0

                channel_comparison[channel] = {
                    'current_revenue': round(float(current_revenue), 2),
                    'last_revenue': round(float(last_revenue), 2),
                    'revenue_change': round(float(revenue_change), 2),
                    'revenue_change_rate': round(float(revenue_change_rate), 2),
                    'current_room_nights': int(current_room_nights),
                    'last_room_nights': int(last_room_nights),
                    'room_nights_change': int(room_nights_change),
                    'room_nights_change_rate': round(float(room_nights_change_rate), 2)
                }

            # 费用类型分析
            fee_type_summary = df.groupby('fee_type').agg(
                revenue=('revenue', 'sum')
            ).sort_values('revenue', ascending=False)
            fee_type_summary['revenue_percent'] = (fee_type_summary['revenue'] / total_accommodation_revenue * 100) if total_accommodation_revenue > 0 else 0

            # 准备最终结果
            report = {
                'total_summary': {
                    'date_range': f"{start_date.replace('-', '.')} - {end_date.replace('-', '.')}",
                    'total_revenue': round(total_accommodation_revenue, 2),  # 住宿费用总计（含钟点房）
                    'room_revenue': round(total_room_revenue, 2),  # 间夜房收入（不含钟点房）
                    'hourly_revenue': round(total_hourly_revenue, 2),  # 钟点房收入
                    'room_nights': int(total_room_nights),
                    'avg_price': round(total_avg_price, 2),  # 平均房价（不含钟点房）
                    'occupancy_rate': round(total_occupancy_rate, 2),
                    'revpar': round(total_revpar, 2)  # RevPAR（基于住宿费用总计）
                },
                'daily_summary': daily_summary.round(2).to_dict(orient='index'),
                'channel_summary': channel_summary.round(2).to_dict(orient='index'),
                'channel_comparison': channel_comparison,  # 新增渠道对比数据
                'comparison_period': f"{last_week_start_str.replace('-', '.')} - {last_week_end_str.replace('-', '.')}",  # 对比周期
                'fee_type_summary': fee_type_summary.round(2).to_dict(orient='index'),
                'pivot_table': pivot_df.round(2).to_html(classes='table table-sm table-bordered', escape=False, sparsify=True)
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

                # 不再进行汇总，直接处理原始订单明细数据
                # 为每个订单生成唯一的order_id
                df['order_id'] = df.apply(lambda row: f"{row['统计渠道']}_{row['record_date']}_{row.name}", axis=1)

                with sqlite3.connect(DATABASE) as conn:
                    cursor = conn.cursor()

                    # 处理每一行原始订单数据
                    for _, row in df.iterrows():
                        try:
                            # 提取数据
                            channel = row['统计渠道']
                            record_date = row['record_date']
                            fee_type = row['房费科目']
                            room_nights = float(row['间夜数'])
                            revenue = float(row['房费'])
                            order_id = row['order_id']
                            guest_name = row.get('客人', '')  # 如果Excel中有客人姓名列

                            # 业务规则：不计入间夜数的费用类型
                            if fee_type in ['加收全天', '手工输入房费', '调整房费']:
                                room_nights = 0

                            # 打印每行数据以便调试
                            print(f"导入数据: 渠道={channel}, 日期={record_date}, 科目={fee_type}, 间夜={room_nights}, 房费={revenue}, 订单ID={order_id}")

                            # 检查是否已存在相同的订单记录（防止重复导入）
                            cursor.execute(
                                "SELECT id FROM DailyRevenue WHERE order_id = ?",
                                (order_id,)
                            )
                            existing_record = cursor.fetchone()

                            if existing_record:
                                # 订单已存在，跳过
                                print(f"订单 {order_id} 已存在，跳过")
                                continue
                            else:
                                # 插入新的订单记录
                                sql = "INSERT INTO DailyRevenue (record_date, channel, fee_type, room_nights, revenue, order_id, guest_name) VALUES (?, ?, ?, ?, ?, ?, ?)"
                                cursor.execute(sql, (record_date, channel, fee_type, room_nights, revenue, order_id, guest_name))
                            
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
# --- 数据库管理路由 ---

def check_admin_password():
    """检查管理员密码"""
    admin_password = os.getenv('DB_ADMIN_PASSWORD')
    if not admin_password:
        return False, "未设置管理员密码"

    if 'admin_authenticated' not in session:
        return False, "未认证"

    return session['admin_authenticated'], "已认证"

@app.route('/db_admin')
def db_admin():
    """数据库管理主页面"""
    # 检查是否已认证
    is_authenticated, message = check_admin_password()
    if not is_authenticated:
        return redirect(url_for('db_admin_login'))

    # 获取数据库统计信息
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()

            # 总记录数
            cursor.execute("SELECT COUNT(*) FROM DailyRevenue")
            total_records = cursor.fetchone()[0]

            # 总收入
            cursor.execute("SELECT SUM(revenue) FROM DailyRevenue")
            total_revenue = cursor.fetchone()[0] or 0

            # 总间夜数
            cursor.execute("SELECT SUM(room_nights) FROM DailyRevenue")
            total_room_nights = cursor.fetchone()[0] or 0

            # 数据库文件大小
            db_size = os.path.getsize(DATABASE)
            db_size_mb = f"{db_size / (1024*1024):.2f} MB"

            stats = {
                'total_records': total_records,
                'total_revenue': total_revenue,
                'total_room_nights': total_room_nights,
                'db_size': db_size_mb
            }

    except Exception as e:
        flash(f'获取统计信息失败: {e}')
        stats = {
            'total_records': 0,
            'total_revenue': 0,
            'total_room_nights': 0,
            'db_size': '0 MB'
        }

    return render_template('db_admin.html', stats=stats)

@app.route('/db_admin/login', methods=['GET', 'POST'])
def db_admin_login():
    """管理员登录页面"""
    if request.method == 'POST':
        password = request.form.get('password')
        admin_password = os.getenv('DB_ADMIN_PASSWORD')

        if not admin_password:
            flash('系统未配置管理员密码')
            return render_template('db_admin_login.html')

        if password == admin_password:
            session['admin_authenticated'] = True
            return redirect(url_for('db_admin'))
        else:
            flash('密码错误')

    return render_template('db_admin_login.html')

@app.route('/db_admin/logout')
def db_admin_logout():
    """管理员登出"""
    session.pop('admin_authenticated', None)
    flash('已安全登出')
    return redirect(url_for('index'))

@app.route('/db_admin/records')
def db_admin_records():
    """获取所有记录"""
    is_authenticated, message = check_admin_password()
    if not is_authenticated:
        return jsonify({'success': False, 'error': '未认证'})

    try:
        with sqlite3.connect(DATABASE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM DailyRevenue ORDER BY record_date DESC, id DESC LIMIT 1000")
            records = [dict(row) for row in cursor.fetchall()]

        return jsonify({'success': True, 'records': records})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/db_admin/record/<int:record_id>')
def db_admin_get_record(record_id):
    """获取单个记录"""
    is_authenticated, message = check_admin_password()
    if not is_authenticated:
        return jsonify({'success': False, 'error': '未认证'})

    try:
        with sqlite3.connect(DATABASE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM DailyRevenue WHERE id = ?", (record_id,))
            record = cursor.fetchone()

            if record:
                return jsonify({'success': True, 'record': dict(record)})
            else:
                return jsonify({'success': False, 'error': '记录不存在'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/db_admin/update', methods=['POST'])
def db_admin_update_record():
    """更新记录"""
    is_authenticated, message = check_admin_password()
    if not is_authenticated:
        return jsonify({'success': False, 'error': '未认证'})

    try:
        data = request.get_json()
        record_id = data.get('id')

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE DailyRevenue
                SET record_date = ?, channel = ?, fee_type = ?,
                    room_nights = ?, revenue = ?, guest_name = ?
                WHERE id = ?
            """, (
                data.get('record_date'),
                data.get('channel'),
                data.get('fee_type'),
                data.get('room_nights'),
                data.get('revenue'),
                data.get('guest_name'),
                record_id
            ))

            if cursor.rowcount > 0:
                conn.commit()
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': '记录不存在'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/db_admin/delete/<int:record_id>', methods=['DELETE'])
def db_admin_delete_record(record_id):
    """删除单个记录"""
    is_authenticated, message = check_admin_password()
    if not is_authenticated:
        return jsonify({'success': False, 'error': '未认证'})

    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM DailyRevenue WHERE id = ?", (record_id,))

            if cursor.rowcount > 0:
                conn.commit()
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': '记录不存在'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/db_admin/delete_batch', methods=['POST'])
def db_admin_delete_batch():
    """批量删除记录"""
    is_authenticated, message = check_admin_password()
    if not is_authenticated:
        return jsonify({'success': False, 'error': '未认证'})

    try:
        data = request.get_json()
        ids = data.get('ids', [])

        if not ids:
            return jsonify({'success': False, 'error': '未选择记录'})

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            placeholders = ','.join(['?'] * len(ids))
            cursor.execute(f"DELETE FROM DailyRevenue WHERE id IN ({placeholders})", ids)
            deleted_count = cursor.rowcount
            conn.commit()

        return jsonify({'success': True, 'deleted_count': deleted_count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/db_admin/clear_all', methods=['POST'])
def db_admin_clear_all():
    """清空所有数据"""
    is_authenticated, message = check_admin_password()
    if not is_authenticated:
        return jsonify({'success': False, 'error': '未认证'})

    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM DailyRevenue")
            deleted_count = cursor.rowcount
            conn.commit()

        return jsonify({'success': True, 'deleted_count': deleted_count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/db_admin/backup', methods=['POST'])
def db_admin_backup():
    """备份数据库"""
    is_authenticated, message = check_admin_password()
    if not is_authenticated:
        return jsonify({'success': False, 'error': '未认证'})

    try:
        # 创建备份目录
        backup_dir = os.path.join(BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        # 生成备份文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'hotel_revenue_backup_{timestamp}.db'
        backup_path = os.path.join(backup_dir, backup_filename)

        # 复制数据库文件
        shutil.copy2(DATABASE, backup_path)

        return jsonify({'success': True, 'backup_file': backup_filename})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/db_admin/export')
def db_admin_export():
    """导出数据为CSV"""
    is_authenticated, message = check_admin_password()
    if not is_authenticated:
        flash('未认证')
        return redirect(url_for('db_admin_login'))

    try:
        with sqlite3.connect(DATABASE) as conn:
            df = pd.read_sql_query("SELECT * FROM DailyRevenue ORDER BY record_date, id", conn)

        # 生成CSV文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f'hotel_revenue_export_{timestamp}.csv'
        csv_path = os.path.join(BASE_DIR, csv_filename)

        df.to_csv(csv_path, index=False, encoding='utf-8-sig')

        return send_file(csv_path, as_attachment=True, download_name=csv_filename)
    except Exception as e:
        flash(f'导出失败: {e}')
        return redirect(url_for('db_admin'))

@app.route('/db_admin/delete_by_date_range', methods=['POST'])
def db_admin_delete_by_date_range():
    """按日期范围删除数据"""
    is_authenticated, message = check_admin_password()
    if not is_authenticated:
        return jsonify({'success': False, 'error': '未认证'})

    try:
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if not start_date or not end_date:
            return jsonify({'success': False, 'error': '请提供开始日期和结束日期'})

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 删除指定日期范围内的记录
        cursor.execute('''
            DELETE FROM revenue_data
            WHERE record_date BETWEEN ? AND ?
        ''', (start_date, end_date))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'deleted_count': deleted_count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/db_admin/clear_database', methods=['POST'])
def db_admin_clear_database():
    """清空整个数据库"""
    is_authenticated, message = check_admin_password()
    if not is_authenticated:
        return jsonify({'success': False, 'error': '未认证'})

    try:
        # 删除数据库文件
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        # 重新初始化数据库
        init_db()

        return jsonify({'success': True, 'message': '数据库已完全清空并重新初始化'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='乐巷酒店数据智能分析系统')
    parser.add_argument('--port', type=int, default=5001, help='Web服务器端口号')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    args = parser.parse_args()
    
    # 确保日志目录存在
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # 配置日志处理器
    log_handler = RotatingFileHandler(os.path.join(LOG_DIR, 'app.log'), maxBytes=10485760, backupCount=5)
    log_handler.setLevel(logging.INFO)
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_handler.setFormatter(log_formatter)
    
    # 添加单独的错误日志
    error_handler = RotatingFileHandler(os.path.join(LOG_DIR, 'error.log'), maxBytes=10485760, backupCount=5)
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
    
    # 记录系统启动信息
    app.logger.info("=== 乐巷酒店数据智能分析系统启动 ===")
    app.logger.info(f"默认使用模型: {DEFAULT_MODEL}")

    # 检查环境变量加载情况
    admin_password = os.getenv('DB_ADMIN_PASSWORD')
    if admin_password:
        app.logger.info("数据库管理密码已配置")
    else:
        app.logger.warning("警告：数据库管理密码未配置！")

    app.logger.info(f"总房间数配置: {os.getenv('TOTAL_ROOMS', '未配置')}")
    app.logger.info("数据库初始化完成")
    app.logger.info(f"启动Web服务器在端口 {args.port}...")
    
    print("\n=== 乐巷酒店数据智能分析系统 ===")
    print(f"默认使用模型: {DEFAULT_MODEL}")
    print("数据库初始化完成")
    print(f"启动Web服务器在端口 {args.port}...")
    
    # 启动Flask应用
    app.run(host='0.0.0.0', port=args.port, debug=args.debug)