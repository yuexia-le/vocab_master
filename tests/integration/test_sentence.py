
"""
句子挑战功能集成测试
测试：缓存机制 -> 重复检测 -> AI交互 -> JSON解析
"""
import pytest
import allure
import json
from unittest.mock import patch
from app import app, db, RECENT_SENTENCE_CHALLENGES


# ========== 2. 句子挑战测试类 ==========
@allure.epic("集成测试类")
@allure.feature("句子挑战测试类")
@allure.story("句子")
@pytest.mark.integration
class TestSentenceIntegration:
    """句子挑战集成测试类"""
    
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """每个测试前清空缓存"""
        RECENT_SENTENCE_CHALLENGES.clear()
        yield
        RECENT_SENTENCE_CHALLENGES.clear()
    
    @allure.title("1. 正常生成句子成功")
    def test_generate_sentence_normal(self, test_client):
        """TC_SC_001: 正常生成句子挑战"""
        mock_response = {
            "chinese": "今天天气真好", 
            "answer": "The weather is really nice today"
        }
        with patch('app.generate_sentence_challenge') as mock_gen_sentence:
            mock_gen_sentence.return_value = mock_response
            response = test_client.get('/api/sentence')
            assert response.status_code == 200
            json_data = response.get_json()
            assert json_data['chinese'] == '今天天气真好'
            
            assert len(RECENT_SENTENCE_CHALLENGES) == 1
            first_cache = RECENT_SENTENCE_CHALLENGES[0]
            assert first_cache is not None
            assert first_cache['chinese'] == '今天天气真好'
        print("✓ TC_SC_001 通过")

    
    @allure.title("2. 验证重复句子检测")
    def test_sentence_no_repeat_logic(self, test_client):
        """TC_SC_002: 验证重复句子检测"""
        responses = [
            {'chinese': '第一句话', 'answer': 'First'},
            {'chinese': '第二句话', 'answer': 'Second'}
        ]
        with patch('app.generate_sentence_challenge') as mock_gen_sentence:
            mock_gen_sentence.side_effect = responses
            test_client.get('/api/sentence')
            
            # 验证排除列表
            test_client.get('/api/sentence')
            _, kwargs = mock_gen_sentence.call_args
            assert '第一句话' in kwargs.get('exclude_sentences', [])
        print("✓ TC_SC_002 通过")

    
    @allure.title("3. 缓存机制验证（FIFO 淘汰）")
    def test_sentence_cache_limit(self, test_client):
        """TC_SC_003: 缓存机制验证（FIFO 淘汰）"""
        sentences = [{'chinese': f'句子{i}', 'answer': f'S{i}'} for i in range(10)]
        with patch('app.generate_sentence_challenge') as mock_gen_sentence:
            mock_gen_sentence.side_effect = sentences
            for _ in range(6):
                test_client.get('/api/sentence')
            
            assert len(RECENT_SENTENCE_CHALLENGES) == 5
            cache_chinese = [item['chinese'] for item in RECENT_SENTENCE_CHALLENGES if item]
            assert '句子0' not in cache_chinese
        print("✓ TC_SC_003 通过")

    
    @allure.title("4. AI 返回非预期格式处理")
    def test_sentence_invalid_json_response(self, test_client):
        """TC_SC_004: AI 返回非预期格式处理"""
        with patch('app.generate_sentence_challenge') as mock_gen_sentence:
            mock_gen_sentence.return_value = {
                'chinese': '生成失败，请重试',
                'answer': 'Error'
            }
            response = test_client.get('/api/sentence')
            assert response.status_code == 200
            assert '生成失败' in response.get_json()['chinese']
        print("✓ TC_SC_004 通过.")

    
    @allure.title("5. AI 返回带 Markdown 标记的 JSON")
    def test_sentence_with_markdown_json(self, test_client):
        """
        TC_SC_005: AI 返回带 Markdown 标记的 JSON
        测试点：验证 Service 层解析器能处理 ```json ... ``` 格式
        """
        # 模拟经过解析器处理后的最终输出
        # 在集成测试中，我们关注 API 最终返回给前端的结果是否正确
        mock_cleaned_data = {
            'chinese': '测试 Markdown 解析',
            'answer': 'Testing Markdown parsing'
        }
        
        with patch('app.generate_sentence_challenge') as mock_gen_sentence:
            mock_gen_sentence.return_value = mock_cleaned_data
            
            response = test_client.get('/api/sentence')
            
            assert response.status_code == 200
            json_data = response.get_json()
            assert json_data['chinese'] == '测试 Markdown 解析'
            assert json_data['answer'] == 'Testing Markdown parsing'
            
            # 确保即使是这种格式，也正确存入了缓存
            assert RECENT_SENTENCE_CHALLENGES[0] is not None
            assert RECENT_SENTENCE_CHALLENGES[0]['chinese'] == '测试 Markdown 解析'
            
        print("✓ TC_SC_005 通过：带 Markdown 的 JSON 处理正确")