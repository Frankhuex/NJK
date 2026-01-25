#!/bin/bash

# 1. 杀掉占用11004端口的旧进程
echo "正在查找并停止11004端口的旧进程..."
OLD_PID=$(sudo lsof -t -i:11004)
if [ ! -z "$OLD_PID" ]; then
    echo "找到旧进程 PID: $OLD_PID，正在终止..."
    sudo kill -9 $OLD_PID
    echo "旧进程已终止"
else
    echo "未找到占用11004端口的进程"
fi

# 2. 激活虚拟环境
echo "激活虚拟环境..."
source .venv/bin/activate

# 3. 启动新进程
echo "启动新进程..."
nohup python3 src/main.py &

echo "启动完成！PID: $!"
echo "日志输出到: nohup.out"
