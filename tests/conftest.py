"""
tests/conftest.py
最简化但最可靠的配置
"""
import pytest
import os
import sys

# ========== 关键：在导入app之前设置环境变量 ==========
os.environ['DB_URL'] = 'sqlite:///:memory:'
os.environ['TESTING'] = 'true'

# ========== 导入app ==========
from app import app, db, Word


@pytest.fixture(scope='session', autouse=True)
def setup_test_environment():
    """
    设置测试环境 - 只在会话开始时执行一次
    """
    print("\n" + "="*60)
    print("设置测试环境")
    print("="*60)
    
    # 备份原始配置
    original_config = {
        'SQLALCHEMY_DATABASE_URI': app.config.get('SQLALCHEMY_DATABASE_URI'),
        'SQLALCHEMY_ENGINE_OPTIONS': app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {}).copy(),
        'TESTING': app.config.get('TESTING', False)
    }
    
    # 设置测试配置
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'connect_args': {'check_same_thread': False}
        }
    })
    
    print(f"测试数据库URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # 创建应用上下文并初始化数据库
    with app.app_context():
        # 创建所有表
        db.create_all()
        print("数据库表创建完成")
    
    yield
    
    # 恢复配置
    print("\n恢复原始配置...")
    for key, value in original_config.items():
        if value is not None:
            app.config[key] = value


@pytest.fixture
def test_client():
    """
    测试客户端fixture - 每个测试函数一个干净的客户端
    """
    # 为每个测试创建新的客户端
    with app.test_client() as client:
        # 每个测试开始时清理数据库
        with app.app_context():
            # 确保表存在
            try:
                db.create_all()
                print("✓ 数据库表创建完成")
            except Exception as e:
                print(f"创建表时出错: {e}")
                # 如果表已存在，继续执行
            
            # 清理数据（使用更安全的方式）
            try:
                # 方法1：使用更安全的清理方式
                from sqlalchemy import text
                db.session.execute(text('DELETE FROM words'))
                db.session.commit()
                print("✓ 数据库数据已清理")
            except Exception as e:
                print(f"清理数据时出错（可能是表不存在）: {e}")
                # 如果表不存在，忽略错误
        
        yield client
        
        # 测试后清理
        with app.app_context():
            try:
                db.session.query(Word).delete()
                db.session.commit()
                db.session.remove()
                print("✓ 测试后清理完成")
            except Exception as e:
                print(f"测试后清理出错: {e}")


@pytest.fixture
def db_session():
    """
    数据库会话fixture
    """
    with app.app_context():
        yield db.session


@pytest.fixture
def sample_words():
    """
    预置测试单词数据
    """
    with app.app_context():
        words_data = [
            {'english': 'apple', 'chinese': '苹果'},
            {'english': 'banana', 'chinese': '香蕉'},
            {'english': 'cat', 'chinese': '猫'},
        ]
        
        words = []
        for data in words_data:
            word = Word(**data)
            db.session.add(word)
            words.append(word)
        
        db.session.commit()
        yield words
        
        # 清理
        db.session.query(Word).delete()
        db.session.commit()


# ========== 注册pytest标记 ==========

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: 标记为集成测试"
    )