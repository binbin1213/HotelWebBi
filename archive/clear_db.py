import sqlite3
import os

# 获取数据库文件路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'hotel_revenue.db')

def clear_database():
    """清空数据库中的所有数据"""
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            # 删除DailyRevenue表中的所有数据
            cursor.execute("DELETE FROM DailyRevenue")
            conn.commit()
            print(f"数据库已清空，共删除 {cursor.rowcount} 条记录")
    except Exception as e:
        print(f"清空数据库时出错: {e}")

if __name__ == "__main__":
    # 确认操作
    confirm = input("警告：此操作将清空所有数据！输入'YES'确认: ")
    if confirm.upper() == "YES":
        clear_database()
    else:
        print("操作已取消") 