source .venv/bin/activate
pip3 install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
nohup python3 -u src/main.py &