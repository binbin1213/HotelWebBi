import sqlite3
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from ai_service import call_ai_api, analyze_data_with_ai, DEFAULT_MODEL

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
            
            if table_exists:
                # 表已存在，需要重新创建以更新约束
                # 先备份现有数据
                cursor.execute("CREATE TABLE IF NOT EXISTS DailyRevenue_backup AS SELECT * FROM DailyRevenue")
                print("现有数据已备份到 DailyRevenue_backup 表")
                
                # 删除原表
                cursor.execute("DROP TABLE DailyRevenue")
                print("原 DailyRevenue 表已删除")
                
                # 创建新表，使用新的唯一约束
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
                print("已创建新的 DailyRevenue 表，唯一约束更新为(record_date, channel, fee_type)")
                
                # 恢复数据
                cursor.execute("""
                    INSERT INTO DailyRevenue (record_date, channel, fee_type, room_nights, revenue)
                    SELECT record_date, channel, fee_type, room_nights, revenue FROM DailyRevenue_backup
                """)
                print(f"已从备份表恢复 {cursor.rowcount} 条记录")
                
            else:
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
    except Exception as e:
        print(f"初始化数据库时出错: {e}")
            conn.commit()
            print("数据库初始化成功")
    except Exception as e:
        print(f"初始化数据库时出错: {e}")

# --- Routes ---

@app.route('/')
def index():
    """
    Renders the main homepage.
    """
    return render_template('home.html')

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
            
            # 根据筛选条件执行不同的查询
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
                                  display_period=display_period)
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
        # 调用AI服务解析查询
        ai_response = call_ai_api(query, model_name=model)
        
        # 提取SQL查询和可视化配置
        sql = ai_response.get('sql')
        chart_type = ai_response.get('chart_type', 'bar')
        x_field = ai_response.get('x_field', 'channel')
        y_field = ai_response.get('y_field', 'revenue')
        title = ai_response.get('title', '数据分析')
        dimensions = ai_response.get('dimensions', [])
        metrics = ai_response.get('metrics', [])
        report_type = ai_response.get('report_type', 'daily')
        
        # 根据解析结果查询数据库
        data = query_database({
            'sql': sql,
            'chart_type': chart_type,
            'x_field': x_field,
            'y_field': y_field,
            'dimensions': dimensions,
            'metrics': metrics,
            'report_type': report_type
        })
        
        # 生成可视化配置
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
        
        # 获取AI洞察
        insights = ai_response.get('insights')
        if not insights:
            # 如果AI响应中没有洞察，使用数据分析生成洞察
            insights = analyze_data_with_ai(query, data, model_name=model)
        
        return jsonify({
            "data": data.to_dict(orient='records'),
            "visualization": visualization,
            "insights": insights
        })
    except Exception as e:
        return jsonify({
            "error": f"处理查询时出错: {str(e)}"
        }), 500

def query_database(query_config):
    """执行SQL查询并返回结果"""
    conn = sqlite3.connect(DATABASE)
    
    try:
        # 执行SQL查询
        df = pd.read_sql_query(query_config['sql'], conn)
        
        # 数据后处理
        
        # 如果是饼图，添加百分比列
        if query_config.get('chart_type') == 'pie' and len(df) > 0:
            y_field = query_config.get('y_field', 'revenue')
            
            # 处理y_field可能是列表的情况
            if isinstance(y_field, list) and len(y_field) > 0:
                primary_y_field = y_field[0]  # 使用列表中的第一个字段
            else:
                primary_y_field = y_field
                
            if primary_y_field in df.columns:
                total = df[primary_y_field].sum()
                if total > 0:
                    df['percentage'] = df[primary_y_field] / total
                else:
                    df['percentage'] = 0
        
        # 如果是热力图，确保数据格式正确
        if query_config.get('chart_type') == 'heatmap' and len(df) > 0:
            dimensions = query_config.get('dimensions', [])
            metrics = query_config.get('metrics', [])
            
            if len(dimensions) >= 2 and len(metrics) >= 1:
                # 确保所有维度组合都有数据点
                dim1_values = df[dimensions[0]].unique()
                dim2_values = df[dimensions[1]].unique()
                
                # 创建所有可能的维度组合
                all_combinations = []
                for val1 in dim1_values:
                    for val2 in dim2_values:
                        all_combinations.append({dimensions[0]: val1, dimensions[1]: val2})
                
                # 检查哪些组合不存在，并添加空值行
                for combo in all_combinations:
                    exists = False
                    for _, row in df.iterrows():
                        if row[dimensions[0]] == combo[dimensions[0]] and row[dimensions[1]] == combo[dimensions[1]]:
                            exists = True
                            break
                    
                    if not exists:
                        new_row = {dimensions[0]: combo[dimensions[0]], dimensions[1]: combo[dimensions[1]]}
                        for metric in metrics:
                            new_row[metric] = 0
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
        # 如果是组合图表，确保数据格式正确
        if query_config.get('chart_type') == 'combo' and len(df) > 0:
            y_field = query_config.get('y_field')
            if isinstance(y_field, list) and len(y_field) > 1:
                # 确保所有Y轴字段都存在
                for field in y_field:
                    if field not in df.columns:
                        df[field] = 0
        
        # 计算平均房价（如果需要且数据允许）
        if 'revenue' in df.columns and 'room_nights' in df.columns:
            # 避免除以零
            df['avg_price'] = np.where(df['room_nights'] > 0, df['revenue'] / df['room_nights'], 0)
        
        # 添加星期几（如果有日期列）
        if 'record_date' in df.columns and 'day_of_week' not in df.columns:
            df['day_of_week'] = pd.to_datetime(df['record_date']).dt.dayofweek
            
            # 将数字星期几转换为名称
            day_names = {0: '周一', 1: '周二', 2: '周三', 3: '周四', 4: '周五', 5: '周六', 6: '周日'}
            df['day_name'] = df['day_of_week'].apply(lambda x: day_names.get(x, ''))
        
        # 如果是周收入分布，确保有所有星期几
        if query_config.get('report_type') == 'weekly' and 'day_name' in df.columns:
            # 检查是否缺少某些星期几
            all_days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            existing_days = df['day_name'].unique().tolist()
            
            # 添加缺失的星期几
            for day in all_days:
                if day not in existing_days:
                    new_row = {'day_name': day}
                    metrics = query_config.get('metrics', [])
                    for metric in metrics:
                        if metric in df.columns:
                            new_row[metric] = 0
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            
            # 确保星期几的顺序正确
            day_order = {day: i for i, day in enumerate(all_days)}
            df['day_order'] = df['day_name'].map(day_order)
            df = df.sort_values('day_order').drop('day_order', axis=1)
        
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

@app.route('/weekly_report')
def weekly_report():
    """渲染周报表页面"""
    # 获取日期范围参数，默认为最近一周
    end_date = request.args.get('end_date', '')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    # 计算开始日期（默认为结束日期的前6天，共7天）
    start_date = request.args.get('start_date', '')
    if not start_date:
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        start_date_obj = end_date_obj - timedelta(days=6)
        start_date = start_date_obj.strftime('%Y-%m-%d')
    
    # 获取周报表数据
    report_data = generate_weekly_report(start_date, end_date)
    
    return render_template('weekly_report.html', 
                          start_date=start_date,
                          end_date=end_date,
                          report_data=report_data)

def generate_weekly_report(start_date, end_date):
    """生成周报表数据"""
    try:
        with sqlite3.connect(DATABASE) as conn:
            # 读取指定日期范围内的数据
            query = """
                SELECT 
                    record_date, 
                    channel, 
                    fee_type,
                    SUM(room_nights) as room_nights, 
                    SUM(revenue) as revenue
                FROM 
                    DailyRevenue
                WHERE 
                    record_date BETWEEN ? AND ?
                GROUP BY 
                    record_date, channel, fee_type
                ORDER BY 
                    record_date, channel, fee_type
            """
            
            params = [start_date, end_date]
            df = pd.read_sql_query(query, conn, params=params)
            
            # 如果没有数据，返回包含默认值的结果
            if df.empty:
                return {
                    "summary": {
                        "total_room_nights": 0.0,
                        "total_revenue": 0.0,
                        "avg_price": 0.0,
                        "date_range": f"{start_date} — {end_date}"
                    },
                    "daily_data": [],
                    "channel_data": [],
                    "detail_data": [],
                    "charts_data": {
                        "room_nights": [],
                        "revenue": [],
                        "avg_price": [],
                        "days": []
                    }
                }
            
            # 将日期列转换为日期类型
            df['record_date'] = pd.to_datetime(df['record_date'])
            
            # 1. 计算总体摘要数据
            # 计算总间夜数（只考虑正常房费，不包括调整房费）
            total_room_nights = df[df['fee_type'] != '调整房费']['room_nights'].sum()
            
            # 计算总收入（包括所有费用科目，调整房费也计入）
            total_revenue = df['revenue'].sum()
            
            # 2. 按渠道汇总数据
            channel_summary = df.groupby('channel').agg({
                'room_nights': 'sum',
                'revenue': 'sum'
            }).reset_index()
            
            # 计算每个渠道的平均房价
            channel_summary['avg_price'] = channel_summary.apply(
                lambda x: x['revenue'] / x['room_nights'] if x['room_nights'] > 0 else 0, 
                axis=1
            )
            
            # 计算占比
            channel_summary['room_nights_pct'] = (channel_summary['room_nights'] / total_room_nights * 100) if total_room_nights > 0 else 0
            channel_summary['revenue_pct'] = (channel_summary['revenue'] / total_revenue * 100) if total_revenue > 0 else 0
            
            # 3. 按日期汇总数据
            date_summary = df.groupby('record_date').agg({
                'room_nights': 'sum',
                'revenue': 'sum'
            }).reset_index()
            
            # 计算每天的平均房价
            date_summary['avg_price'] = date_summary.apply(
                lambda x: x['revenue'] / x['room_nights'] if x['room_nights'] > 0 else 0, 
                axis=1
            )
            
            # 添加星期几信息
            day_names = {
                0: '周一',
                1: '周二',
                2: '周三',
                3: '周四',
                4: '周五',
                5: '周六',
                6: '周日'
            }
            date_summary['day_name'] = date_summary['record_date'].dt.dayofweek.map(day_names)
            
            # 将日期范围内的所有日期生成为DataFrame
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            date_range = pd.date_range(start=start_dt, end=end_dt)
            all_dates_df = pd.DataFrame({'record_date': date_range})
            all_dates_df['day_name'] = all_dates_df['record_date'].dt.dayofweek.map(day_names)
            
            # 4. 生成图表数据
            # 4.1 间夜折线图数据
            room_nights_chart = []
            for channel in df['channel'].unique():
                # 只考虑正常房费的间夜数，不包括调整房费
                channel_data = df[(df['channel'] == channel) & (df['fee_type'] != '调整房费')].copy()
                
                # 按日期汇总该渠道的间夜数
                channel_dates = channel_data.groupby('record_date').agg({
                    'room_nights': 'sum'
                }).reset_index()
                
                # 确保每个渠道都有完整的日期范围
                channel_dates = pd.merge(
                    all_dates_df[['record_date', 'day_name']],
                    channel_dates,
                    on='record_date',
                    how='left'
                )
                # 填充缺失值
                channel_dates['room_nights'] = channel_dates['room_nights'].fillna(0)
                
                # 按日期排序
                channel_dates = channel_dates.sort_values(by='record_date')
                
                room_nights_chart.append({
                    'name': channel,
                    'type': 'line',
                    'data': channel_dates[['day_name', 'room_nights']].values.tolist()
                })
            
            # 4.2 收入折线图数据
            revenue_chart = []
            for channel in df['channel'].unique():
                # 包括所有费用科目的收入，调整房费也计入
                channel_data = df[df['channel'] == channel].copy()
                
                # 按日期汇总该渠道的收入
                channel_dates = channel_data.groupby('record_date').agg({
                    'revenue': 'sum'
                }).reset_index()
                
                # 确保每个渠道都有完整的日期范围
                channel_dates = pd.merge(
                    all_dates_df[['record_date', 'day_name']],
                    channel_dates,
                    on='record_date',
                    how='left'
                )
                # 填充缺失值
                channel_dates['revenue'] = channel_dates['revenue'].fillna(0)
                
                # 按日期排序
                channel_dates = channel_dates.sort_values(by='record_date')
                
                revenue_chart.append({
                    'name': channel,
                    'type': 'line',
                    'data': channel_dates[['day_name', 'revenue']].values.tolist()
                })
            
            # 4.3 平均房价折线图数据
            avg_price_chart = []
            for channel in df['channel'].unique():
                # 按日期和渠道分组计算平均房价
                channel_data = df[df['channel'] == channel].copy()
                channel_avg = channel_data.groupby('record_date').agg({
                    'room_nights': 'sum',
                    'revenue': 'sum'
                }).reset_index()
                
                # 计算平均房价
                channel_avg['avg_price'] = channel_avg.apply(
                    lambda x: x['revenue'] / x['room_nights'] if x['room_nights'] > 0 else 0, 
                    axis=1
                )
                
                # 确保每个渠道都有完整的日期范围
                channel_dates = pd.merge(
                    all_dates_df[['record_date', 'day_name']],
                    channel_avg[['record_date', 'avg_price']],
                    on='record_date',
                    how='left'
                )
                # 填充缺失值
                channel_dates['avg_price'] = channel_dates['avg_price'].fillna(0)
                
                # 按日期排序
                channel_dates = channel_dates.sort_values(by='record_date')
                
                avg_price_chart.append({
                    'name': channel,
                    'type': 'line',
                    'data': channel_dates[['day_name', 'avg_price']].values.tolist()
                })
            
            # 5. 计算出租率（如果有总房间数据）
            # 这里假设每天有20个房间可供出租
            total_rooms_per_day = 20
            date_summary['occupancy_rate'] = date_summary['room_nights'] / (total_rooms_per_day) * 100
            
            # 转换数据为前端可用格式
            # 将日期对象转换为字符串格式
            date_summary_dict = date_summary.to_dict(orient='records')
            for item in date_summary_dict:
                if isinstance(item['record_date'], pd.Timestamp):
                    item['record_date'] = item['record_date'].strftime('%Y-%m-%d')
            
            df_dict = df.to_dict(orient='records')
            for item in df_dict:
                if isinstance(item['record_date'], pd.Timestamp):
                    item['record_date'] = item['record_date'].strftime('%Y-%m-%d')
            
            # 确保日期顺序正确
            ordered_days = []
            for date in date_range:
                day_name = day_names.get(date.dayofweek, '')
                if day_name not in ordered_days:
                    ordered_days.append(day_name)
            
            return {
                "summary": {
                    "total_room_nights": float(total_room_nights),
                    "total_revenue": float(total_revenue),
                    "avg_price": float(total_revenue / total_room_nights) if total_room_nights > 0 else 0,
                    "date_range": f"{start_date} — {end_date}"
                },
                "channel_data": channel_summary.to_dict(orient='records'),
                "daily_data": date_summary_dict,
                "detail_data": df_dict,
                "charts_data": {
                    "room_nights": room_nights_chart,
                    "revenue": revenue_chart,
                    "avg_price": avg_price_chart,
                    "days": ordered_days
                }
            }
    except Exception as e:
        print(f"生成周报表时出错: {e}")
        return {
            "error": str(e),
            "summary": {},
            "daily_data": {},
            "channel_data": {},
            "charts_data": {}
        }

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
        
        if file and file.filename.endswith(('.xlsx', '.xls')):
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
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='乐巷酒店数据智能分析系统')
    parser.add_argument('--port', type=int, default=5001, help='Web服务器端口号')
    args = parser.parse_args()
    
    init_db()
    print("=== 乐巷酒店数据智能分析系统 ===")
    print(f"默认使用模型: {DEFAULT_MODEL}")
    print("数据库初始化完成")
    print(f"启动Web服务器在端口 {args.port}...")
    app.run(debug=True, host='0.0.0.0', port=args.port)