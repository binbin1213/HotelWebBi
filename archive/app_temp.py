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

