let currentWords = [];
let currentAnswer = "";
// 增加翻译任务队列
let translationQueue = [];
let isTranslating = false;

// 1. 获取单词数据 (增加一个参数来控制是否需要刷新admin列表)
async function fetchWords(isAdmin = false) {
    const res = await fetch('/api/words');
    const newWords = await res.json();
    
    // 无论是主页还是后台，都更新全局列表
    currentWords = newWords;

    // 如果是管理页面，将数据存为全局变量并渲染列表
    if (isAdmin) {
        renderAdminList();
        // --- 核心修改：重新填充翻译队列 ---
        translationQueue = []; // 先清空，再填充
        newWords.forEach(word => {
            // 如果单词的中文是“待翻译...”或“翻译失败（API 错误）”，重新加入队列
            if (word.chinese === "待翻译..." || word.chinese.includes("翻译失败")) {
                translationQueue.push(word.id);
            }
        });
        
        // 启动/继续翻译队列
        if (translationQueue.length > 0) {
            startTranslationQueue();
        }
    } else {
       // 主页：使用全局列表进行渲染
       const currentMode = document.querySelector('.controls button.active')?.id.replace('btn-', '') || 'all';
       renderCards(currentMode);
    }
}

// 2. 渲染背诵卡片（修改：接受传入的单词列表）
function renderCards(mode) {
    const container = document.getElementById('word-list');
    if (!container) return;
    
    // 始终使用全局 currentWords
    const wordsToRender = currentWords;
    
    container.innerHTML = '';

    // 检查是否有单词需要渲染（解决显示模式下为空白的问题）
    if (wordsToRender.length === 0) {
        container.innerHTML = '<p style="text-align: center;">词库为空，请前往后台上传单词。</p>';
        return;
    }

    wordsToRender.forEach(word => {
        const card = document.createElement('div');
        card.className = 'word-card';
        
        let enClass = mode === 'cn' ? 'blur' : '';
        let cnClass = mode === 'en' ? 'blur' : '';

        card.innerHTML = `
            <div class="word-en ${enClass}" onclick="this.classList.toggle('blur')">${word.english}</div>
            <div class="word-cn ${cnClass}" onclick="this.classList.toggle('blur')">${word.chinese || '翻译中...'}</div>
        `;
        container.appendChild(card);
    });

    // 只有在主页调用时才更新按钮状态
    if(document.getElementById(`btn-${mode}`)) {
        document.querySelectorAll('.controls button').forEach(b => b.classList.remove('active'));
        document.getElementById(`btn-${mode}`).classList.add('active');
    }
}

function setView(mode) {
    renderCards(mode);
}

// 4. 异步翻译函数 (核心优化)
async function startTranslationQueue() {
    if (isTranslating || translationQueue.length === 0) {
        isTranslating = false;
        return; 
    }

    isTranslating = true;
    const wordId = translationQueue.shift(); // 取出第一个 ID
    const status = document.getElementById('upload-status');
    status.innerText = `正在翻译 ID ${wordId}，队列剩余 ${translationQueue.length} 个。`;
    
    try {
        const res = await fetch(`/api/translate_word/${wordId}`, { method: 'POST' });
        const data = await res.json();
        
        if (res.status === 200) {
            // ****** 核心优化点：局部更新 DOM ******
            const cnElement = document.getElementById(`chinese-${wordId}`);
            if (cnElement) {
                cnElement.innerText = data.chinese; // 直接更新中文列的内容
            }
            
            // 顺便更新主页的列表数据（如果它已加载）
            const wordToUpdate = currentWords.find(w => w.id === wordId);
            if(wordToUpdate) {
                wordToUpdate.chinese = data.chinese;
            }
            
            console.log(`Word ${wordId} translated to: ${data.chinese}`);
        } else {
            // 翻译失败
            const cnElement = document.getElementById(`chinese-${wordId}`);
            let errorStatus = "翻译失败（API 错误）";
           
            // 只要不是成功的状态，都重新排队
            translationQueue.push(wordId);

            if (data.error) {
                errorStatus = `翻译失败 (${res.status} ${data.error.substring(0, 15)}...，将重试)`;
            } else if (res.status !== 200) {
                 errorStatus = `翻译失败 (HTTP ${res.status}，将重试)`;
            }
            
            if (cnElement) {
                cnElement.innerText = errorStatus; 
            }
            console.warn(`Word ${wordId} failed (HTTP ${res.status}), retrying later.`);
        }
    } catch (e) {
        // 网络请求失败时，也重新入队
        translationQueue.push(wordId);
        console.error('Translation fetch error:', e, 'Retrying.');
    } finally {
        isTranslating = false;
        // 无论成功还是失败，等待 3 秒再处理下一个单词
        setTimeout(startTranslationQueue, 3000); 
    }
}

// 5. 修改 uploadFile 函数（保持不变，它只负责启动队列）
async function uploadFile() {
    const fileInput = document.getElementById('fileInput');
    const status = document.getElementById('upload-status');
    
    if (!fileInput.files[0]) return alert('请选择文件');

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    status.innerText = '正在上传并保存英文单词...';
    
    try {
        const res = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        
        status.innerText = data.message || data.error;

        // 立即刷新列表，以便用户看到“待翻译...”状态
        fetchWords(true); 

        if (data.new_words && data.new_words.length > 0) {
            translationQueue = data.new_words.map(w => w.id);
            startTranslationQueue();
        }
        
    } catch (e) {
        status.innerText = '上传失败';
    }
}

// 删除单词
async function deleteWord(id) {
    if(!confirm('确定删除?')) return;
    await fetch(`/api/words/${id}`, { method: 'DELETE' });
    fetchWords(true);
}

// 3. 渲染后台列表（使用 index 作为序号）
function renderAdminList() {
        const tbody = document.getElementById('admin-list');
        // 使用 map 的第二个参数 (index) 来生成从 1 开始的序号
        tbody.innerHTML = currentWords.map((w, index) => `
            <tr id="word-row-${w.id}" style="border-bottom: 1px solid #eee;">
                <td style="padding: 10px;">${index + 1}</td> 
                <td>${w.english}</td>
                <td id="chinese-${w.id}">${w.chinese}</td>
                <td><button style="padding: 5px 10px; background: #ff7675; color: white;" onclick="deleteWord(${w.id})">删除</button></td>
            </tr>
        `).join('');
    }

// 生成故事
async function generateStory() {
    const box = document.getElementById('story-box');
    box.innerHTML = 'AI 正在创作故事... ⏳';
    const res = await fetch('/api/story', { method: 'POST' });
    const data = await res.json();
    box.innerHTML = data.story;
}

// 造句练习
async function loadSentence() {
    document.getElementById('answer-box').style.display = 'none';
    document.getElementById('user-input').value = '';
    const res = await fetch('/api/sentence');
    const data = await res.json();
    document.getElementById('challenge-cn').innerText = data.chinese;
    currentAnswer = data.answer;
}

function checkSentence() {
    const ansBox = document.getElementById('answer-box');
    ansBox.innerHTML = `参考答案: ${currentAnswer}`;
    ansBox.style.display = 'block';
}

// 初始化
if (location.pathname === '/') {
    fetchWords();
    loadSentence();
}