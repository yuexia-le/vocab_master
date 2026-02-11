
"""
故事生成功能集成测试
测试：单词选择 -> AI生成 -> 格式验证 -> 错误处理
"""
import pytest
import time
from unittest.mock import patch, MagicMock
import allure
from app import app, db, Word

# ========== 3. 故事生成测试类 ==========
@allure.epic("集成测试类")
@allure.feature("故事生成测试类")
@allure.story("故事")
@pytest.mark.integration
class TestStoryIntegration:
    """故事生成集成测试类"""
    
    @allure.title("1. 正常生成故事成功")
    def test_generate_story_normal(self, test_client):
        """TC_ST_001: 正常生成故事"""
        # 1. 准备测试数据 (解决报红写法)
        with app.app_context():
            db.session.query(Word).delete()
            words_data = [
                ('apple', '苹果'), ('banana', '香蕉'), ('cat', '猫'),
                ('dog', '狗'), ('elephant', '大象'), ('fish', '鱼'),
                ('giraffe', '长颈鹿'), ('house', '房子'), ('ice', '冰'),
                ('jacket', '夹克')
            ]
            for eng, cn in words_data:
                word = Word()
                word.english = eng
                word.chinese = cn
                db.session.add(word)
            db.session.commit()
        
        # 2. Mock AI 响应
        mock_story = "Once upon a time, there was an <b>apple</b>."
        
        with patch('app.generate_story') as mock_gen_story:
            mock_gen_story.return_value = mock_story
            
            response = test_client.post('/api/story')
            
            assert response.status_code == 200
            json_data = response.get_json()
            assert json_data['story'] == mock_story
            mock_gen_story.assert_called_once()
            
            # 验证传递参数
            call_args = mock_gen_story.call_args[0][0]
            assert isinstance(call_args, list)
            assert len(call_args) == 10

    @allure.title("2. 空数据库处理")
    def test_generate_story_empty_database(self, test_client):
        """TC_ST_002: 空数据库处理"""
        with app.app_context():
            db.session.query(Word).delete()
            db.session.commit()
        
        with patch('app.generate_story') as mock_gen_story:
            response = test_client.post('/api/story')
            assert response.status_code == 200
            assert '词库为空' in response.get_json()['story']
            mock_gen_story.assert_not_called()

    @allure.title("3. AI服务速率限制")
    def test_generate_story_rate_limit(self, test_client):
    # 先确保数据库中有数据
        with app.app_context():
            db.session.query(Word).delete()  # 先清理数据库
            word = Word()
            word.english = 'test'
            word.chinese = '测试'
            db.session.add(word)
            db.session.commit()
            print("数据库单词数:", db.session.query(Word).count())  # 调试信息

        with patch('app.generate_story') as mock_gen_story:
            mock_gen_story.side_effect = Exception("API rate limit exceeded, please try again later")
            
            response = test_client.post('/api/story')
            
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.get_json()}")
            print("Mock是否被调用:", mock_gen_story.called)
            print("Mock调用参数:", mock_gen_story.call_args if mock_gen_story.called else None)

            # 确保不是空数据库响应
            response_data = response.get_json()
            if '词库为空' in response_data['story']:
                print("错误：返回了空数据库消息，但数据库应该包含数据")
                assert False, "测试数据未正确设置"
            
            assert response.status_code == 429
            assert '操作太快啦' in response_data['story']
            mock_gen_story.assert_called_once()

    @allure.title("4. AI服务异常")
    def test_generate_story_ai_error(self, test_client):
        """TC_ST_004: AI服务异常 (返回 None)"""
        with app.app_context():
            word = Word()
            word.english = 'test'
            word.chinese = '测试'
            db.session.add(word)
            db.session.commit()
    
        with patch('app.generate_story') as mock_gen_story:
            mock_gen_story.return_value = None
            response = test_client.post('/api/story')
            
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.get_json()}")
            
            assert response.status_code == 500
            assert 'AI 助手暂时掉线了' in response.get_json()['story']

    @allure.title("5. 连续多次生成故事")
    def test_generate_story_multiple_times(self, test_client):
        """TC_ST_006: 连续多次生成故事"""
        with app.app_context():
            db.session.query(Word).delete() # 先清空避免干扰
            for i in range(20):
                word = Word()
                word.english = f'word{i}'
                word.chinese = f'单词{i}'
                db.session.add(word)
            db.session.commit()
        
        stories = []
        for i in range(3):
            with patch('app.generate_story') as mock_gen_story:
                mock_text = f"Story {i} with <b>word{i}</b>."
                mock_gen_story.return_value = mock_text
                
                response = test_client.post('/api/story')
                assert response.status_code == 200
                stories.append(response.get_json()['story'])
            
            time.sleep(0.1)
        
        assert len(stories) == 3
        # 验证故事内容不完全一致
        assert len(set(stories)) == 3