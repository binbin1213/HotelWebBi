#!/bin/bash

# 激活虚拟环境
source venv/bin/activate

# 运行Flask应用
python app.py

# 如果想在后台运行，可以使用以下命令替代上面的命令
# nohup python app.py > app.log 2>&1 & 