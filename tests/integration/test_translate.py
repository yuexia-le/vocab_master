# tests/integration/test_translate.py
"""
翻译功能集成测试
测试：翻译触发 -> AI服务 -> 数据库更新 -> 状态管理
"""
import pytest
import json
import allure
from unittest.mock import patch, MagicMock
from app import app, db, Word


# ========== 翻译集成测试类 ==========
@allure.epic("集成测试类")
@allure.feature("翻译测试类")
@allure.story("单词翻译")
@pytest.mark.integration
class TestTranslateIntegration:
    """翻译功能集成测试类"""
    
    @pytest.fixture(autouse=True)
    def setup_words(self, test_client):  # 修改这里：client -> test_client
        """每个测试前设置测试数据"""
        with app.app_context():
            # 清空并创建测试单词
            db.session.query(Word).delete()
            
            # 创建待翻译的单词 1
            word1 = Word()
            word1.english = 'apple'
            word1.chinese = '待翻译...'
            
            # 创建已翻译的单词 2
            word2 = Word()
            word2.english = 'banana'
            word2.chinese = '香蕉'
            
            # 创建待翻译的单词 3
            word3 = Word()
            word3.english = 'cat'
            word3.chinese = '待翻译...'
            
            db.session.add_all([word1, word2, word3])
            db.session.commit()
            
            # 保存ID供测试使用
            self.word1_id = word1.id
            self.word2_id = word2.id
            self.word3_id = word3.id
    
    @allure.title("1. 单个单词翻译成功")
    def test_translate_single_word_success(self, test_client):  # 修改这里：client -> test_client
        """
        TC_TR_001: 单个单词翻译成功
        """
        # 1. Mock AI翻译服务
        with patch('app.get_translation') as mock_translate:
            mock_translate.return_value = "苹果, 苹果树"
            
            # 2. 调用翻译API
            response = test_client.post(f'/api/translate_word/{self.word1_id}')  # 修改这里
            
            # 3. 验证HTTP响应
            assert response.status_code == 200
            
            # 4. 验证JSON响应
            json_data = response.get_json()
            assert json_data['message'] == '翻译成功'
            assert json_data['chinese'] == '苹果, 苹果树'
            
            # 5. 验证AI被正确调用
            mock_translate.assert_called_once_with('apple')
            
            # 6. 验证数据库更新
            with app.app_context():
                word = db.session.get(Word, self.word1_id)
                assert word is not None
                assert word.chinese == '苹果, 苹果树'
        
        print("✓ TC_TR_001 通过：单个单词翻译成功")
    
    @allure.title("2. 单词已翻译或不存在")
    def test_translate_already_translated_word(self, test_client):  # 修改这里
        """
        TC_TR_002: 翻译已完成的单词
        """
        with patch('app.get_translation') as mock_translate:
            response = test_client.post(f'/api/translate_word/{self.word2_id}')  # 修改这里
            
            assert response.status_code == 200
            json_data = response.get_json()
            assert json_data['message'] == '单词已翻译或不存在'
            
            mock_translate.assert_not_called()
            
            with app.app_context():
                word = db.session.get(Word, self.word2_id)
                assert word is not None
                assert word.chinese == '香蕉'
        
        print("✓ TC_TR_002 通过：已翻译单词正确处理")
    
    @allure.title("3. 处理不存在的单词")
    def test_translate_nonexistent_word(self, test_client):  # 修改这里
        """
        TC_TR_003: 翻译不存在的单词
        """
        non_existent_id = 9999
        
        with patch('app.get_translation') as mock_translate:
            response = test_client.post(f'/api/translate_word/{non_existent_id}')  # 修改这里
            
            assert response.status_code == 200
            json_data = response.get_json()
            assert '单词已翻译或不存在' in json_data['message']
            
            mock_translate.assert_not_called()
        
        print("✓ TC_TR_003 通过：不存在的单词处理正确")
    
    @allure.title("4. AI翻译服务异常（速率限制）")
    def test_translate_rate_limit_error(self, test_client):  # 修改这里
        """
        TC_TR_004: AI翻译服务异常（速率限制）
        """
        with patch('app.get_translation') as mock_translate:
            mock_translate.side_effect = Exception("Rate limit exceeded")
            
            response = test_client.post(f'/api/translate_word/{self.word3_id}')  # 修改这里
            
            assert response.status_code == 500
            json_data = response.get_json()
            assert 'error' in json_data
            assert '翻译失败，可能是速率限制' in json_data['error']
            
            with app.app_context():
                word = db.session.get(Word, self.word3_id)
                assert word is not None
                assert word.chinese == '待翻译...'
        
        print("✓ TC_TR_004 通过：速率限制错误处理正确")
    
    @allure.title("5. 批量单词连续翻译")
    def test_batch_translate_flow(self, test_client):  # 修改这里
        """
        TC_TR_006: 批量单词连续翻译
        """
        # 创建更多待翻译单词
        with app.app_context():
            for i in range(5):
                word = Word()
                word.english = f'test{i}'
                word.chinese = '待翻译...'
                db.session.add(word)
            db.session.commit()
            
            # 获取所有待翻译单词的ID
            pending_words = Word.query.filter_by(chinese='待翻译...').all()
            word_ids = [w.id for w in pending_words]
        
        # Mock AI翻译
        translation_map = {
            'apple': '苹果',
            'cat': '猫',
            'test0': '测试0',
            'test1': '测试1',
            'test2': '测试2', 
            'test3': '测试3',
            'test4': '测试4'
        }
        
        def mock_translate(word_text):
            return translation_map.get(word_text, '未知')
        
        with patch('app.get_translation', side_effect=mock_translate):
            # 连续调用翻译API
            success_count = 0
            for word_id in word_ids:
                response = test_client.post(f'/api/translate_word/{word_id}')  # 修改这里
                if response.status_code == 200:
                    success_count += 1
            
            # 验证所有调用都成功
            assert success_count == len(word_ids)
            
            # 验证数据库全部更新
            with app.app_context():
                translated_words_count = Word.query.filter(
                    Word.chinese != '待翻译...'
                ).count()
                # 初始数据中有1个已翻译(banana)，新翻译了7个(apple, cat + 5个test)
                assert translated_words_count == 8
        
        print("✓ TC_TR_006 通过：批量翻译流程正常")