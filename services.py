# services.py
import os
import json
from config import Config

# 直接使用底层http客户端，绕过OpenAI客户端的proxies问题
import requests

API_KEY = os.getenv("DEEPSEEK_API_KEY", Config.DEEPSEEK_API_KEY)
#"https://api.siliconflow.cn/v1"
BASE_URL = "https://api.deepseek.com"
MODEL_NAME = "deepseek-chat"

def get_translation(word):
    """获取单词翻译"""
    if not API_KEY:
        return "请配置 API KEY"
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": "你是一个翻译助手。直接输出该英文单词最常用的3个中文意思，用逗号分隔。不要输出拼音或其他解释。"},
                    {"role": "user", "content": word}
                ],
                "temperature": 0.3
            },
            timeout=30
        )
        
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            return content.strip() if content else "翻译为空"
        else:
            return f"翻译服务暂时不可用: {response.status_code}"
    except Exception as e:
        print(f"AI Error: {e}")
        
        return "翻译服务暂时不可用"

def generate_story(words_list):
    """根据单词列表生成故事"""
    if not words_list or len(words_list) == 0:
        return "请提供单词列表"
    if not API_KEY:
        return "请配置 API KEY"
    
    words_str = ", ".join(words_list)
    try:
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": "你是一个英语老师。请用以下单词写一个200字左右的有趣英文短篇故事。请务必将用到的单词用 <b></b> 标签加粗显示，例如 <b>apple</b>。"},
                    {"role": "user", "content": f"单词列表: {words_str}"}
                ],
                "temperature": 0.7
            },
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"生成故事出错: {response.status_code}"
    except Exception as e:
        return f"生成故事出错: {str(e)}"

def generate_sentence_challenge(exclude_sentences=None):
    """生成中文造句题目"""
    prompt = "来一个句子"
    if exclude_sentences:
        exclusion_list = "\\n".join(exclude_sentences)
        prompt += f"不能重复以下中文句子：\\n{exclusion_list}"
    
    if not API_KEY:
        return {"chinese": "请配置API Key", "answer": "Please configure API Key"}

    try:
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": "生成一个常用的中文句子，并提供对应的标准英文翻译。只能返回纯JSON格式，不要用markdown代码块包裹。格式：{\"chinese\": \"...\", \"answer\": \"...\"}"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                #"response_format": {"type": "json_object"}
            },
            timeout=30
        )
        
        if response.status_code == 200:
            # 获取响应内容
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            
            # 清理可能存在的 markdown 符号
            content = content.replace('```json', '').replace('```', '').strip()
            
            # 尝试解析JSON
            try:
                # 查找JSON内容（有时候AI会返回额外文字）
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group()
                
                data = json.loads(content)
                # 确保返回的数据包含必要的字段
                if "chinese" in data and "answer" in data:
                    return data
                else:
                    print(f"返回数据缺少必要字段: {data}")
                    return {"chinese": "生成失败，格式错误", "answer": "Error"}
                    
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {e}")
                print(f"原始内容: {content}")
                
                # 备选方案：尝试从文本中提取
                return {"chinese": content[:50], "answer": "请重试"}
        else:
            # 打印详细的错误信息
            print(f"API错误: {response.status_code}")
            print(f"响应内容: {response.text}")
            return {"chinese": f"生成失败: HTTP {response.status_code}", "answer": "Error"}
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {"chinese": "生成失败，请重试", "answer": "Error"}
