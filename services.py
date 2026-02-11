# services.py - 完全移除proxies参数
import os
import json
from config import Config

# 直接使用底层http客户端，绕过OpenAI客户端的proxies问题
import requests

API_KEY = os.getenv("SILICONFLOW_API_KEY", Config.SILICONFLOW_API_KEY)
BASE_URL = "https://api.siliconflow.cn/v1"
MODEL_NAME = "deepseek-ai/DeepSeek-V3"

def get_translation(word):
    """获取单词翻译"""
    if not API_KEY:
        return "请配置 API KEY"
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat/completions",
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
            f"{BASE_URL}/chat/completions",
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
            f"{BASE_URL}/chat/completions",
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
                "response_format": {"type": "json_object"}
            },
            timeout=30
        )
        
        if response.status_code == 200:
            content = response.text  # 使用 .text 而不是 .json()
            
            # 如果内容为空
            if not content or content.strip() == '':
                return {"chinese": "生成内容为空", "answer": "Error"}
            
            # 清理可能存在的 markdown 符号
            content = content.strip()
            content = content.replace('```json', '').replace('```', '').strip()
            
            # 尝试解析JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                print(f"JSON解析错误: {content}")
                return {"chinese": "生成失败，请重试", "answer": "Error"}
        else:
            return {"chinese": f"生成失败: HTTP {response.status_code}", "answer": "Error"}
            
    except Exception as e:
        print(f"Error: {e}")
        return {"chinese": "生成失败，请重试", "answer": "Error"}