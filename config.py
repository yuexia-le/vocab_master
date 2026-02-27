# config.py
import os

class Config:
    # 请根据实际情况修改数据库连接信息
    # 格式: mysql+pymysql://用户名:密码@主机/数据库名
    SQLALCHEMY_DATABASE_URI = os.getenv('DB_URL', 'mysql+pymysql://root:root@localhost/vocab_master')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # AI 配置 
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    SILICONFLOW_BASE_URL = "https://api.deepseek.com"