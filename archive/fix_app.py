with open('app.py', 'r') as file:
    content = file.read()

# 修复第一个问题：备份表SQL语句中的换行符
content = content.replace('DailyRevenue_backup AS SELECT * FROM DailyRevenue\n")', 'DailyRevenue_backup AS SELECT * FROM DailyRevenue")')

# 修复第二个问题：恢复数据SQL语句中的换行符
content = content.replace('FROM DailyRevenue_backup\n', 'FROM DailyRevenue_backup')

with open('app_fixed.py', 'w') as file:
    file.write(content)

print("修复完成，新文件已保存为 app_fixed.py")
