FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量，确保 Python 输出直接打印到日志（方便 CI/CD 查看报错）
ENV PYTHONUNBUFFERED=1

# 安装必要的系统依赖（如果你的 pymysql 需要底层支持）
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# 先拷贝依赖文件并安装（利用 Docker 缓存层）
COPY requirements.txt .
# 使用阿里云或清华镜像源可以加速构建（如果是 GitHub Actions 构建则无需设置，云端带宽很快）
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝项目所有代码
COPY . .

# 生产环境建议不要直接运行 python app.py（Flask 自带服务器性能弱）
# 如果你的镜像里装了 gunicorn，可以换成下面这行：
# CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]

# 目前保持原样即可
CMD ["python", "app.py"]