# tests/unit/test_services.py - 修复版

import pytest
import json
import allure
from unittest.mock import patch, MagicMock, Mock

# 要测试的函数
from services import get_translation, generate_story, generate_sentence_challenge
from config import Config

pytestmark = pytest.mark.unit

# ==================== Allure 标签定义 ====================
TRANSLATION_FEATURE = "翻译功能"
SENTENCE_FEATURE = "句子生成功能"
STORY_FEATURE = "故事生成功能"
NORMAL_TEST = "正常流程"
EXCEPTION_TEST = "异常处理"
BOUNDARY_TEST = "边界测试"
INPUT_VALIDATION = "输入验证"

BLOCKER = allure.severity_level.BLOCKER
CRITICAL = allure.severity_level.CRITICAL
NORMAL = allure.severity_level.NORMAL

# ==================== 辅助函数 ====================
#参数：内容、状态码200、是否是JSON，根据源码设置
def create_mock_response(content, status_code=200, is_json=True):
    """创建模拟的requests响应对象"""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    
    if is_json:
        # 设置json方法的返回值
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": content
                    }
                }
            ]
        }
    else:
        # 模拟非JSON响应（如markdown、空内容等）
        mock_response.json.side_effect = ValueError("Invalid JSON")
    
    # 模拟 .text 属性、获取响应体文本内容
    mock_response.text = content
    
    return mock_response

# ==================== 翻译功能测试 ====================
@allure.epic("AI服务单元测试")
@allure.feature(TRANSLATION_FEATURE)
class TestTranslation:
    
    @allure.story("正常翻译流程")
    @allure.title("成功获取单词翻译")
    @allure.severity(BLOCKER)
    @patch("services.requests.post")
    def test_get_translation_success(self, mock_post):
        """TC-TR-001: 正常翻译流程"""
        test_word = "apple"
        expected_translation = "苹果, 苹果树, 苹果派"
        
        mock_post.return_value = create_mock_response(expected_translation)
        
        result = get_translation(test_word)
        
        with allure.step("验证返回的翻译结果"):
            assert result == expected_translation
        
        with allure.step("验证AI被正确调用"):
            # 验证requests.post被调用了一次
            mock_post.assert_called_once()
            call_args = mock_post.call_args[1]  # 获取kwargs
            messages = call_args['json']['messages']
            user_content = messages[1]['content']
            assert user_content == test_word

    @allure.story("异常处理")
    @allure.title("API Key缺失处理")
    @allure.severity(CRITICAL)
    def test_get_translation_api_key_missing(self):
        """TC-TR-002: API Key缺失异常"""
        with patch("services.API_KEY", new=''):  
            result = get_translation("test")
            assert result == "请配置 API KEY"

    @allure.story("异常处理")
    @allure.title("AI服务调用异常处理")
    @allure.severity(CRITICAL)
    @patch("services.requests.post")  
    def test_get_translation_api_exception(self, mock_post):
        """TC-TR-003: AI服务异常"""
        mock_post.side_effect = Exception("翻译服务暂时不可用")
        
        result = get_translation("test")
        
        assert "翻译服务暂时不可用" in result

    @allure.story("异常处理")
    @allure.title("AI返回空内容处理")
    @allure.severity(NORMAL)
    @patch("services.requests.post")  # 🔥 修改这里
    def test_get_translation_empty_response(self, mock_post):
        """TC-TR-004: AI返回空内容"""
        mock_post.return_value = create_mock_response("")
        
        result = get_translation("test")
        
        assert result == "翻译为空"

    @allure.story("边界测试")
    @allure.title("超长单词翻译")
    @allure.severity(NORMAL)
    @patch("services.requests.post")  # 🔥 修改这里
    def test_get_translation_long_word(self, mock_post):
        """TC-TR-005: 超长单词边界测试"""
        long_word = "pneumonoultramicroscopicsilicovolcanoconiosis"
        expected = "尘肺病"
        
        mock_post.return_value = create_mock_response(expected)
        
        result = get_translation(long_word)
        
        with allure.step("验证翻译结果"):
            assert result == expected
        
        with allure.step("验证传递完整的超长单词"):
            call_args = mock_post.call_args[1]
            messages = call_args['json']['messages']
            user_content = messages[1]['content']
            assert user_content == long_word

    @allure.story("输入验证")
    @allure.title("特殊字符处理 - {word}")
    @allure.severity(NORMAL)
    @pytest.mark.parametrize("word, expected", [
        ("test-word", "测试-单词"),
        ("don't", "不要"),
        ("test@example", "测试@示例"),
        ("a&b", "A和B"),
    ])
    @patch("services.requests.post")
    def test_get_translation_special_characters(self, mock_post, word, expected):
        """TC-TR-006: 特殊字符处理"""
        mock_post.return_value = create_mock_response(expected)
        # 重置mock
        mock_post.reset_mock()
        
        result = get_translation(word)
        
        with allure.step(f"验证单词 '{word}' 翻译结果"):
            assert result == expected
        
        with allure.step("验证传递完整的单词"):
            call_args = mock_post.call_args[1]
            messages = call_args['json']['messages']
            user_content = messages[1]['content']
            assert user_content == word

# ==================== 句子生成功能测试 ====================
@allure.epic("AI服务单元测试")
@allure.feature(SENTENCE_FEATURE)
class TestSentenceChallenge:
    
    @allure.story("正常流程")
    @allure.title("成功生成句子挑战")
    @allure.severity(BLOCKER)
    @patch("services.requests.post")  # 🔥 修改这里
    def test_generate_sentence_challenge_success(self, mock_post):
        """TC-SC-001: 正常生成句子挑战"""
        mock_json_response = '{"chinese": "今天天气真好", "answer": "The weather is really nice today"}'
        mock_post.return_value = create_mock_response(mock_json_response)
        
        result = generate_sentence_challenge(exclude_sentences=["避免这个句子"])
        
        with allure.step("验证返回字典类型"):
            assert isinstance(result, dict)
        
        with allure.step("验证包含必要字段"):
            assert "chinese" in result
            assert "answer" in result
        
        with allure.step("验证字段值正确"):
            assert result["chinese"] == "今天天气真好"
            assert result["answer"] == "The weather is really nice today"

    @allure.story("异常处理")
    @allure.title("非法JSON格式处理")
    @allure.severity(CRITICAL)
    @patch("services.requests.post")  # 🔥 修改这里
    def test_generate_sentence_challenge_invalid_json(self, mock_post):
        """TC-SC-002: 返回非法JSON"""
        mock_post.return_value = create_mock_response('这是一个非法的JSON字符串')
        
        result = generate_sentence_challenge()
        
        with allure.step("验证异常被优雅处理"):
            assert "生成失败" in result["chinese"] or "Error" in result["answer"]
            assert isinstance(result, dict)
            assert "chinese" in result
            assert "answer" in result

    @allure.story("数据处理")
    @allure.title("Markdown代码块处理")
    @allure.severity(allure.severity_level.NORMAL)
    @patch("services.requests.post")
    def test_generate_sentence_challenge_markdown_json(self, mock_post):
        """TC-SC-003: 返回带markdown的JSON"""
        mock_content = '```json\n{"chinese": "测试", "answer": "test"}\n```'
        
        # 创建一个更真实的mock响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_content  # 设置.text属性
        mock_response.json.side_effect = ValueError("Invalid JSON")  # .json()抛出异常
        mock_post.return_value = mock_response
        
        result = generate_sentence_challenge()
        
        assert result["chinese"] == "测试"
        assert result["answer"] == "test"

    @allure.story("异常处理")
    @allure.title("空内容处理")
    @allure.severity(NORMAL)
    @patch("services.requests.post")  
    def test_generate_sentence_challenge_empty_response(self, mock_post):
       
        """TC-SC-004: 返回空内容"""
        # 创建一个返回空内容的mock响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ''  # 空内容
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response
        
        result = generate_sentence_challenge()
        
        assert "生成内容为空" in result["chinese"]
        assert result["answer"] == "Error"

    @allure.story("业务逻辑")
    @allure.title("排除重复句子功能")
    @allure.severity(NORMAL)
    @patch('services.requests.post')  # 🔥 修改这里
    def test_generate_sentence_challenge_exclude_logic(self, mock_post):
        """TC-SC-005: 验证排除重复句子逻辑"""
        exclude_list = ["不要生成这个", "这个也不要", "还有这个"]
        expected_prompt_contains = "不能重复以下中文句子"
        
        def capture_call(*args, **kwargs):
            return create_mock_response('{"chinese": "新句子", "answer": "new sentence"}')
        
        mock_post.side_effect = capture_call
        
        result = generate_sentence_challenge(exclude_sentences=exclude_list)
        
        with allure.step("验证AI被正确调用"):
            assert mock_post.call_count == 1
        
        with allure.step("验证排除逻辑被包含在提示词中"):
            call_args = mock_post.call_args[1]
            user_message = call_args['json']['messages'][1]['content']
            assert expected_prompt_contains in user_message

# ==================== 故事生成功能测试 ====================
@allure.epic("AI服务单元测试")
@allure.feature(STORY_FEATURE)
class TestStoryGeneration:
    
    @allure.story("正常流程")
    @allure.title("成功生成故事")
    @allure.severity(BLOCKER)
    @patch("services.requests.post")  # 🔥 修改这里
    def test_generate_story_success(self, mock_post):
        """TC-SG-001: 正常生成故事"""
        words_list = ["apple", "banana", "cat"]
        expected_story = "Once upon a time, there was an <b>apple</b> and a <b>banana</b> and a <b>cat</b>."
        
        mock_post.return_value = create_mock_response(expected_story)
        
        result = generate_story(words_list)
        
        with allure.step("验证返回的故事内容"):
            assert result == expected_story
            assert "<b>" in result
        
        with allure.step("验证所有单词都传递给AI"):
            call_args = mock_post.call_args[1]
            messages = call_args['json']['messages']
            user_content = messages[1]['content']
            for word in words_list:
                assert word in user_content

    @allure.story("输入验证")
    @allure.title("空单词列表处理")
    @allure.severity(CRITICAL)
    def test_generate_story_empty_words_list(self):
        """TC-SG-002: 空单词列表处理"""
        result = generate_story([])
        
        with allure.step("验证返回错误提示"):
            assert result is not None
            assert "请提供单词列表" in result

    @allure.story("异常处理")
    @allure.title("AI服务异常处理")
    @allure.severity(CRITICAL)
    @patch("services.requests.post")  # 🔥 修改这里
    def test_generate_story_api_exception(self, mock_post):
        """TC-SG-003: AI服务异常"""
        mock_post.side_effect = Exception("生成故事出错")
        
        result = generate_story(["apple"])
        
        with allure.step("验证异常被捕获并返回错误信息"):
            assert result is not None
            assert "生成故事出错" in result
            assert isinstance(result, str)

    @allure.story("输入验证")
    @allure.title("特殊字符处理")
    @allure.severity(NORMAL)
    @patch('services.requests.post')  # 🔥 修改这里
    def test_generate_story_special_characters(self, mock_post):
        """TC-SG-004: 单词列表包含特殊字符"""
        words_with_special = ["test-word", "don't", "a&b"]
        expected_story = "A story with special words."
        
        mock_post.return_value = create_mock_response(expected_story)
        
        result = generate_story(words_with_special)
        
        with allure.step("验证函数能正常处理特殊字符"):
            assert result == expected_story
        
        with allure.step("验证所有单词都传递给了AI"):
            call_args = mock_post.call_args[1]
            user_content = call_args['json']['messages'][1]['content']
            for word in words_with_special:
                assert word in user_content