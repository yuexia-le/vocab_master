"""
tests/integration/test_upload.py
文件上传功能集成测试
依赖：conftest.py 中的 test_client fixture
"""
import pytest
import json
import allure
import time
from io import BytesIO
from unittest.mock import patch

# 只需要从app导入必要的模型和组件
from app import app, db, Word


# ========== 测试类 ==========
@allure.epic("集成测试类")
@allure.feature("文件上传测试类")
@allure.story("文件上传")
@pytest.mark.integration
class TestUploadIntegration:
    """文件上传集成测试类"""
    
    # ========== 测试用例 1-3：基础上传功能 ==========
    
    @allure.title("1. 上传纯英文txt文件")
    def test_upload_english_only(self, test_client):
        """
        TC_UP_001: 上传纯英文txt文件
        测试点：英文解析、待翻译标记、数据库存储
        """
        # 1. 准备测试数据
        file_content = "apple\nbanana\ncat\ndog\nelephant"
        
        # 2. 创建模拟文件
        data = {
            'file': (BytesIO(file_content.encode('utf-8')), 'test_en.txt')
        }
        
        # 3. 执行上传
        response = test_client.post('/api/upload', data=data)
        
        # 4. 验证HTTP响应
        assert response.status_code == 200, f"上传失败，状态码：{response.status_code}"
        
        # 5. 验证JSON响应
        json_data = response.get_json()
        assert 'message' in json_data
        assert '成功导入 5 个新单词' in json_data['message']
        assert 'new_words' in json_data
        assert len(json_data['new_words']) == 5
        
        # 6. 验证数据库
        with app.app_context():
            words = Word.query.all()
            assert len(words) == 5
            
            # 验证每个单词的状态
            for word in words:
                assert word.english in ['apple', 'banana', 'cat', 'dog', 'elephant']
                assert word.chinese == '待翻译...', f"单词{word.english}应标记为待翻译"
        
        print("✓ TC_UP_001 通过：纯英文文件上传成功")
    
    @allure.title("2. 上传中英混合txt文件")
    def test_upload_mixed_english_chinese(self, test_client):
        """
        TC_UP_002: 上传中英混合txt文件
        测试点：中英文识别、免翻译标记、正确解析
        """
        # 1. 准备混合内容
        file_content = """apple 苹果
                        banana 香蕉
                        cat
                        狗 dog
                        测试 test"""
        
        data = {'file': (BytesIO(file_content.encode('utf-8')), 'mixed.txt')}
        
        # 2. 使用Mock避免实际调用AI
        with patch('app.get_translation') as mock_translate:
            # 只模拟cat的翻译
            mock_translate.return_value = "猫"
            
            # 3. 执行上传
            response = test_client.post('/api/upload', data=data)
            
            # 4. 验证响应
            assert response.status_code == 200
            json_data = response.get_json()
            assert '成功导入 5 个新单词' in json_data['message']
            
            # 5. 验证AI调用次数
            # 注意：上传时不会立即调用翻译，所以应该是0次
            assert mock_translate.call_count == 0
        
        # 6. 验证数据库具体内容
        with app.app_context():
            words = Word.query.order_by(Word.id).all()
            
            # 创建验证字典 - 根据app.py的解析逻辑：
            expected_data = {
                'apple': '苹果',    # 中英文都有，直接使用
                'banana': '香蕉',   # 中英文都有，直接使用
                'cat': '待翻译...', # 只有英文，待翻译
                '狗': 'dog',        # 中文在前，取"狗"为英文，"dog"为中文
                '测试': 'test'      # 中文在前，取"测试"为英文，"test"为中文
            }
            
            for word in words:
                expected_chinese = expected_data.get(word.english)
                assert expected_chinese is not None, f"未知单词：{word.english}"
                assert word.chinese == expected_chinese, f"单词{word.english}翻译不正确：期望'{expected_chinese}'，实际'{word.chinese}'"
        
        print("✓ TC_UP_002 通过：中英混合文件解析正确")
    
    @allure.title("3. 上传空txt文件")
    def test_upload_empty_file(self, test_client):
        """
        TC_UP_003: 上传空txt文件
        测试点：空文件处理、友好提示
        """
        # 1. 空文件
        data = {'file': (BytesIO(b''), 'empty.txt')}
        
        # 2. 上传
        response = test_client.post('/api/upload', data=data)
        
        # 3. 验证
        assert response.status_code == 200
        
        json_data = response.get_json()
        assert '成功导入 0 个新单词' in json_data['message']
        assert json_data['new_words'] == []
        
        # 4. 数据库应该没有新增
        with app.app_context():
            count = Word.query.count()
            assert count == 0, "空文件不应该创建任何记录"
        
        print("✓ TC_UP_003 通过：空文件处理正确")
    
    @allure.title("4. 上传只有空白行的文件")
    def test_upload_file_with_whitespace_lines(self, test_client):
        """
        测试：上传只有空白行的文件
        """
        file_content = "\n\n\n\t\n"
        data = {'file': (BytesIO(file_content.encode('utf-8')), 'whitespace.txt')}
        
        response = test_client.post('/api/upload', data=data)
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert '成功导入 0 个新单词' in json_data['message']
        assert json_data['new_words'] == []
        
        print("✓ TC_UP_004 通过：空白行文件处理正确")
    
    # ========== 测试用例 4-5：边界情况处理 ==========
    
    @allure.title("5. 上传重复单词的文件")
    def test_upload_duplicate_words(self, test_client):
        """
        TC_UP_005: 上传包含重复单词的文件
        测试点：去重逻辑、数据库唯一性
        """
        # 1. 先创建一个单词
        with app.app_context():
            w1 = Word()
            w1.english = 'apple'
            w1.chinese = '苹果'
            db.session.add(w1)
            db.session.commit()
        
        # 2. 上传包含重复单词的文件
        file_content = "apple\nbanana\napple\nbanana\ncat"
        data = {'file': (BytesIO(file_content.encode('utf-8')), 'duplicate.txt')}
        
        # 3. 执行上传
        response = test_client.post('/api/upload', data=data)
        
        # 4. 验证
        assert response.status_code == 200
        json_data = response.get_json()
        
        # 应该只新增2个单词（banana, cat，apple已存在）
        assert '成功导入 2 个新单词' in json_data['message']
        
        # 5. 验证数据库总数
        with app.app_context():
            words = Word.query.all()
            # 原来有1个apple，新增banana和cat，总共3个
            assert len(words) == 3
            
            # 验证具体单词
            english_words = [w.english for w in words]
            assert 'apple' in english_words
            assert 'banana' in english_words
            assert 'cat' in english_words
            assert english_words.count('apple') == 1, "apple应该只有一条记录"
            assert english_words.count('banana') == 1, "banana应该只有一条记录"
        
        print("✓ TC_UP_005 通过：重复单词去重正确")
    
    @allure.title("6. 上传特殊格式文件")
    def test_upload_special_characters(self, test_client):
        """
        TC_UP_007: 上传特殊格式文件
        测试点：特殊字符处理、数据库存储
        """
        file_content = "test-word\ncan't\na&b\nhello_world\n123test"
        data = {'file': (BytesIO(file_content.encode('utf-8')), 'special.txt')}
        
        response = test_client.post('/api/upload', data=data)
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert '成功导入 5 个新单词' in json_data['message']
        
        with app.app_context():
            words = Word.query.all()
            assert len(words) == 5
            
            # 验证特殊字符被正确存储
            special_words = ["test-word", "can't", "a&b", "hello_world", "123test"]
            for word in words:
                assert word.english in special_words
                assert word.chinese == '待翻译...'
        
        print("✓ TC_UP_007 通过：特殊字符处理正确")
    
    # ========== 测试用例 8-9：错误处理 ==========
    @allure.title("7. 上传没有文件部分")
    def test_upload_no_file_part(self, test_client):
        """
        TC_UP_009: 上传没有文件部分
        测试点：请求验证、错误响应
        """
        # 发送不包含文件的POST请求
        response = test_client.post('/api/upload', data={})
        
        # 根据源码，应该返回400
        assert response.status_code == 400
        
        json_data = response.get_json()
        assert 'error' in json_data
        assert json_data['error'] == 'No file part'
        
        print("✓ TC_UP_009 通过：无文件部分错误处理正确")
    
    @allure.title("8. 上传非法格式拦截")
    def test_upload_wrong_file_format(self, test_client):
        """TC_UP_010: 验证非txt文件被优雅拦截（返回400而非崩溃）"""
        bad_data = b'\x00\x01\x02\x03\x04\x05' * 50 
        data = {'file': (BytesIO(bad_data), 'bad.bin')}
        
        response = test_client.post('/api/upload', data=data)
        
        # 现在预期是 400，因为后端捕获了异常
        assert response.status_code == 400
        assert "非法" in response.get_json()['error'] or "无法识别" in response.get_json()['error']
        print("✓ TC_UP_010 通过：非txt文件处理正确")
    
    @allure.title("9. 上传大文件")
    def test_upload_large_file_performance(self, test_client):
        """
        TC_UP_006: 上传大文件（性能测试）
        测试点：性能、内存使用、响应时间
        """
        # 生成1000个不重复的单词
        words = [f"word_{i:04d}" for i in range(1000)]
        file_content = "\n".join(words)
        
        data = {'file': (BytesIO(file_content.encode('utf-8')), 'large.txt')}
        
        # 记录开始时间
        start_time = time.time()
        
        # 执行上传
        response = test_client.post('/api/upload', data=data)
        
        # 计算耗时
        elapsed_time = time.time() - start_time
        
        # 验证
        assert response.status_code == 200, f"大文件上传失败：{response.status_code}"
        assert elapsed_time < 10.0, f"上传时间过长：{elapsed_time:.2f}秒"
        
        json_data = response.get_json()
        assert '成功导入 1000 个新单词' in json_data['message']
        
        # 验证数据库计数
        with app.app_context():
            count = Word.query.count()
            assert count == 1000, f"数据库记录数不正确：{count}"
        
        print(f"✓ TC_UP_006 通过：大文件上传性能正常（{elapsed_time:.2f}秒）")
    
    @allure.title("10. 上传包含制表符和空格的文件")
    def test_upload_file_with_tabs_and_spaces(self, test_client):
        """
        额外的测试：上传包含制表符和空格的文件
        """
        file_content = "  apple  \t 苹果 \n\tbanana\t香蕉\t\n  cat  "
        data = {'file': (BytesIO(file_content.encode('utf-8')), 'tabs.txt')}
        
        response = test_client.post('/api/upload', data=data)
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert '成功导入' in json_data['message']
        
        print("✓ 制表符和空格处理正确")


# ========== 额外的独立测试函数 ==========
@allure.title("11. 上传多个文件")
def test_upload_multiple_files_sequentially(test_client):
    """
    测试连续上传多个文件
    """
    # 第一个文件
    file1_content = "apple\nbanana"
    data1 = {'file': (BytesIO(file1_content.encode('utf-8')), 'file1.txt')}
    
    response1 = test_client.post('/api/upload', data=data1)
    assert response1.status_code == 200
    assert '成功导入 2 个新单词' in response1.get_json()['message']
    
    # 第二个文件
    file2_content = "cat\ndog"
    data2 = {'file': (BytesIO(file2_content.encode('utf-8')), 'file2.txt')}
    
    response2 = test_client.post('/api/upload', data=data2)
    assert response2.status_code == 200
    assert '成功导入 2 个新单词' in response2.get_json()['message']
    
    # 验证总数
    with app.app_context():
        total_words = Word.query.count()
        assert total_words == 4
    
    print("✓ 连续上传多个文件测试通过")

@allure.title("12. 上传文件编码自动识别测试 (GBK)")
def test_upload_file_encoding_gbk(test_client):
    content = (
            "apple 苹果\n"
            "banana 香蕉\n"
            "orange 橘子\n"
            "watermelon 西瓜\n"
            "strawberry 草莓"
        )
    gbk_data = content.encode('gbk')
    data = {'file': (BytesIO(gbk_data), 'test_gbk.txt')}
        
    response = test_client.post('/api/upload', data=data)
        
    assert response.status_code == 200
    words = [w['english'] for w in response.get_json()['new_words']]
    assert "apple" in words
    assert "banana" in words
    print("✓ 文件编码测试通过")



# ========== 如果需要，可以添加setup/teardown ==========

@pytest.fixture(autouse=True)
def cleanup_database():
    """
    每个测试后自动清理数据库
    这个fixture会自动应用于类中的所有测试
    """
    # 测试前：确保数据库干净
    with app.app_context():
        # 删除所有现有数据
        db.session.query(Word).delete()
        db.session.commit()
    
    yield  # 执行测试
    
    # 测试后：再次清理
    with app.app_context():
        db.session.query(Word).delete()
        db.session.commit()