# services.py
import openai
from config import Config
import json

# 1. 初始化客户端：指向硅基流动
client = openai.OpenAI(
    api_key=Config.SILICONFLOW_API_KEY, 
    base_url=Config.SILICONFLOW_BASE_URL
)

# 2. 定义模型名称
# 注意：你需要使用硅基流动支持的模型 ID。
# 推荐使用: "deepseek-ai/DeepSeek-V3" (性价比极高) 
# 或者: "Qwen/Qwen2.5-72B-Instruct"
MODEL_NAME = "deepseek-ai/DeepSeek-V3" 

def get_translation(word):
    """获取单词翻译"""
    # 检查 Key 是否存在
    if not Config.SILICONFLOW_API_KEY:
        return "请配置 API KEY"
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,  # <--- 使用配置的模型
            messages=[
                {"role": "system", "content": "你是一个翻译助手。直接输出该英文单词最常用的3个中文意思，用逗号分隔。不要输出拼音或其他解释。"},
                {"role": "user", "content": word}
            ],
            temperature=0.3 # 翻译需要准确，温度设低一点
        )
        content = response.choices[0].message.content
        if content: # 如果内容不为空
            return content.strip()
        return "翻译为空" # 如果内容为空的兜底
    except Exception as e:
        print(f"AI Error: {e}")
        return "翻译服务暂时不可用"

def generate_story(words_list):
    """根据单词列表生成故事"""
    if not words_list or len(words_list) == 0:
        return "请提供单词列表"
    if not Config.SILICONFLOW_API_KEY:
        return "请配置 API KEY"
    
    words_str = ", ".join(words_list)
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME, # <--- 使用配置的模型
            messages=[
                {"role": "system", "content": "你是一个英语老师。请用以下单词写一个200字左右的有趣英文短篇故事。请务必将用到的单词用 <b></b> 标签加粗显示，例如 <b>apple</b>。"},
                {"role": "user", "content": f"单词列表: {words_str}"}
            ],
            temperature=0.7 # 写故事可以稍微发散一点
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"生成故事出错: {str(e)}"

def generate_sentence_challenge(exclude_sentences=None):
    prompt = "来一个句子"
    if exclude_sentences:
        # 要求 AI 避开最近的句子
        exclusion_list = "\\n".join(exclude_sentences)
        prompt += f"不能重复以下中文句子：\\n{exclusion_list}"
    
    """生成中文造句题目"""
    if not Config.SILICONFLOW_API_KEY:
        return {"chinese": "请配置API Key", "answer": "Please configure API Key"}

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME, # <--- 使用配置的模型
            messages=[
                {"role": "system", "content": "生成一个常用的中文句子，并提供对应的标准英文翻译。只能返回纯JSON格式，不要用markdown代码块包裹。格式：{\"chinese\": \"...\", \"answer\": \"...\"}"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"} # 如果模型支持 json mode 最好，不支持也没关系，下面有处理
        )
        
        content = response.choices[0].message.content
        # 清理可能存在的 markdown 符号 (以防模型不听话)
        # 先判断是否为空
        if not content:
            return {"chinese": "生成内容为空", "answer": "Error"}
        # 确认不为空后，再进行 replace 操作
        content = content.replace('```json', '').replace('```', '').strip()
        
        return json.loads(content)
    except Exception as e:
        print(f"Error: {e}")
        return {"chinese": "生成失败，请重试", "answer": "Error"}