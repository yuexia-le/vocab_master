# app.py
from flask import Flask, render_template, request, jsonify
from config import Config
from models import db, Word
from services import get_translation, generate_story, generate_sentence_challenge
import os
import re # 引入正则表达式库
import sys
import chardet # 引入字符编码检测库

# 判断是否在测试环境中
TESTING = 'pytest' in sys.modules or 'unittest' in sys.modules or os.getenv('TESTING') == 'true'

# 定义一个正则表达式来匹配大部分中文字符
CHINESE_CHAR_PATTERN = re.compile(r'[\u4e00-\u9fff]')

# 引入一个简单的全局缓存，存储最近的句子挑战，用于避免重复
RECENT_SENTENCE_CHALLENGES = []
MAX_CACHE_SIZE = 5

app = Flask(__name__)

if TESTING:
    # 测试环境：使用SQLite，禁用连接池
    app.config.update({
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'TESTING': True,
        'SQLALCHEMY_ENGINE_OPTIONS': {}  # 空配置，避免连接池参数
    })
else:
    # 生产环境：使用原始配置
    app.config.from_object(Config)
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_recycle": 300, 
        "pool_size": 10,
        "pool_timeout": 10 
    }

db.init_app(app)

# 初始化数据库
# with app.app_context():
#     db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

# --- API 接口 ---

@app.route('/api/words', methods=['GET'])
def get_words():
    words = Word.query.all()
    return jsonify([w.to_dict() for w in words])

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    
    # 1. 读取原始二进制数据
    raw_data = file.read()
    if not raw_data:
        return jsonify({'message': '成功导入 0 个新单词', 'new_words': []}), 200

    # 2. 自动检测编码
    result = chardet.detect(raw_data)
    encoding = result['encoding'] or 'utf-8'
    confidence = result['confidence']

    if confidence < 0.3:
        encoding = 'utf-8' # 兜底策略

    try:
        content = raw_data.decode(encoding)
    except Exception:
        # 如果自动识别的编码解码失败，尝试用 utf-8 强制解码
        try:
            content = raw_data.decode('utf-8')

        except Exception:
            return jsonify({'error': '无法识别该文件编码'}), 400

    if raw_data and content is None:
        return jsonify({'error': '文件解码失败'}), 400

    # 情况 2：检测是否是二进制乱码（比如图片）
    # 我们只对“非空字符串”进行乱码检测
    # 如果字符串里包含 \x00 (零字节)，通常它是二进制文件，直接拦截
    if '\x00' in content:
        return jsonify({'error': '文件内容非法：检测到二进制流'}), 400

    # 4. 初始化变量 (必须在循环前)
    lines = content.splitlines()
    count = 0
    new_words_list = [] 
    
    # 5. 核心业务处理 
    for line in lines:
        line = line.strip()
        if not line:
            continue

        eng = ""
        cn = '待翻译...'
        needs_translation = True
        
        parts = line.split() 
        if not parts:
            continue
            
        eng = parts[0].strip()
        
        # 检查是否包含中文或有多部分内容
        if CHINESE_CHAR_PATTERN.search(line) or len(parts) > 1:
            if len(parts) > 1:
                # 使用 maxsplit 确保只拆分第一个空格，保留完整的中文描述
                _, cn_raw = line.split(maxsplit=1) 
                cn = cn_raw.strip()
                needs_translation = False 
        
        # 查重并存入数据库
        if eng and not Word.query.filter_by(english=eng).first():
            new_word = Word()
            new_word.english = eng 
            new_word.chinese = cn 
            db.session.add(new_word)
            db.session.flush() # 获取生成的 ID
            new_words_list.append(new_word.to_dict())
            count += 1
            
    # 6. 提交事务并返回
    db.session.commit()
    return jsonify({
        'message': f'成功导入 {count} 个新单词。',
        'new_words': new_words_list
    })

# --- 增加一个专门用于触发翻译的 API ---
@app.route('/api/translate_word/<int:word_id>', methods=['POST'])
def translate_word_api(word_id):
    word = Word.query.get(word_id)
    if not word or word.chinese != "待翻译...":
        return jsonify({'message': '单词已翻译或不存在'}), 200
        
    try:
        # 调用 AI 翻译
        cn = get_translation(word.english) 
        
        word.chinese = cn
        db.session.commit()
        return jsonify({'message': '翻译成功', 'chinese': cn}), 200
    except Exception as e:
        # 如果速率限制触发，返回特定的错误代码
        return jsonify({'error': '翻译失败，可能是速率限制', 'details': str(e)}), 500

@app.route('/api/words/<int:id>', methods=['DELETE'])
def delete_word(id):
    word = Word.query.get_or_404(id)
    db.session.delete(word)
    db.session.commit()
    return jsonify({'message': 'Deleted'}),200

@app.route('/api/story', methods=['POST'])
def get_story():
    try:
        # 获取随机 10 个单词生成故事
        words = Word.query.order_by(db.func.random()).limit(10).all()
        word_list = [w.english for w in words]
        
        if not word_list:
            return jsonify({'story': '词库为空，请先上传单词。'})
        
        story = generate_story(word_list)
        
        if story and isinstance(story, str):
            if "limit exceeded" in story.lower():
                return jsonify({'story': '操作太快啦！请 30 秒后再试。'}), 429
            return jsonify({'story': story})
        else:
            # 如果 story 是 None 或其他非字符串
            return jsonify({'story': 'AI 助手暂时掉线了，请稍后再试。'}), 500
    
    except Exception as e:
        error_message = str(e).lower()
        
        # 检查异常消息中是否包含速率限制关键词
        if any(keyword in error_message for keyword in ['rate limit', 'limit exceeded', 'too many', 'quota']):
            return jsonify({'story': '操作太快啦！请 30 秒后再试。'}), 429
        
        # 其他异常
        return jsonify({'story': f'生成失败: {str(e)}'}), 500

@app.route('/api/sentence', methods=['GET'])
def get_sentence():
   # 传递缓存中的句子，要求AI避开它们
    recent_cn_sentences = [item['chinese'] for item in RECENT_SENTENCE_CHALLENGES]
    
    # 修改 generate_sentence_challenge 函数，让它接受一个排除列表
    data = generate_sentence_challenge(exclude_sentences=recent_cn_sentences)
    
    if data:
        # 更新缓存
        RECENT_SENTENCE_CHALLENGES.append(data)
        if len(RECENT_SENTENCE_CHALLENGES) > MAX_CACHE_SIZE:
            RECENT_SENTENCE_CHALLENGES.pop(0) # 移除最旧的句子
            
    return jsonify(data)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # 只有手动运行 app.py 时才会连接真实数据库
    app.run(host='0.0.0.0', port=5000, debug=True)

