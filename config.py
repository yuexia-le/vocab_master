# config.py
import os

class Config:
    # 请根据实际情况修改数据库连接信息
    # 格式: mysql+pymysql://用户名:密码@主机/数据库名
    SQLALCHEMY_DATABASE_URI = os.getenv('DB_URL', 'mysql+pymysql://root:root@db_host/vocab_master')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # AI 配置 (这里以兼容 OpenAI 格式的 API 为例，如 DeepSeek 或 ChatGPT)
    # 如果没有 Key，services.py 会使用模拟数据
    SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
    SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"