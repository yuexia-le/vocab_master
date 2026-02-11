
# """
# 完整用户流程集成测试
# 测试：端到端流程、数据一致性、并发处理
# """
# import pytest
# import json
# import threading
# from io import BytesIO
# from unittest.mock import patch
# from app import app, db, Word, RECENT_SENTENCE_CHALLENGES

# # ========== 2. 完整流程测试类 ==========
# @pytest.mark.e2e
# @pytest.mark.integration
# class TestCompleteFlow:
#     """完整流程集成测试类"""
    
#     def test_complete_user_flow(self, test_client):
#         """TC_FLOW_001: 完整用户流程：上传→翻译→生成故事→句子挑战"""
        
#         # --- 步骤1: 上传单词文件 ---
#         file_content = "apple\nbanana 香蕉\ncat\ndog\n"
#         data = {'file': (BytesIO(file_content.encode('utf-8')), 'words.txt')}
        
#         # 上传时不触发翻译
#         response = test_client.post('/api/upload', data=data)
#         assert response.status_code == 200
#         assert '成功导入 4 个新单词' in response.get_json()['message']
        
#         # --- 步骤2: 验证数据库状态 ---
#         with app.app_context():
#             words = Word.query.order_by(Word.id).all()
#             assert len(words) == 4
#             # 验证具体数据，确保上传解析逻辑正确
#             for w in words:
#                 if w.english == 'banana':
#                     assert w.chinese == '香蕉'
#                 else:
#                     assert w.chinese == '待翻译...'
        
#         # --- 步骤3: 触发单词翻译 ---
#         with app.app_context():
#             # 找到待翻译的词
#             pending_words = Word.query.filter_by(chinese='待翻译...').all()
#             word_ids = [w.id for w in pending_words]
        
#         with patch('app.get_translation') as mock_translate:
#             # 模拟 AI 依次返回翻译
#             mock_translate.side_effect = ['苹果', '猫', '狗']
            
#             for word_id in word_ids:
#                 res = test_client.post(f'/api/translate_word/{word_id}')
#                 assert res.status_code == 200
        
#         # --- 步骤4: 生成故事 ---
#         with patch('app.generate_story') as mock_gen_story:
#             mock_story = "Once upon a time, there was an <b>apple</b>."
#             mock_gen_story.return_value = mock_story
            
#             res = test_client.post('/api/story')
#             assert res.status_code == 200
#             assert res.get_json()['story'] == mock_story

#         # --- 步骤5: 生成句子挑战 ---
#         RECENT_SENTENCE_CHALLENGES.clear()
#         with patch('app.generate_sentence_challenge') as mock_gen_sentence:
#             mock_gen_sentence.return_value = {'chinese': '测试', 'answer': 'test'}
#             res = test_client.get('/api/sentence')
#             assert res.status_code == 200
#             assert len(RECENT_SENTENCE_CHALLENGES) == 1
        
#         # --- 步骤6: 验证最终闭环状态 ---
#         with app.app_context():
#             untranslated_count = Word.query.filter_by(chinese='待翻译...').count()
#             assert untranslated_count == 0  # 最终所有词都应该完成了翻译
            
#     def test_concurrent_uploads(self, test_client):
#         """TC_FLOW_002: 并发用户上传（压力与一致性测试）"""
#         results = []
#         errors = []
        
#         def upload_worker(content, name):
#             try:
#                 # 注意：在多线程中使用 client 需要谨慎，此处模拟并发请求
#                 data = {'file': (BytesIO(content.encode('utf-8')), name)}
#                 resp = test_client.post('/api/upload', data=data)
#                 results.append(resp.status_code)
#             except Exception as e:
#                 errors.append(str(e))
        
#         file_contents = [
#             "f1_w1\nf1_w2", "f2_w1\nf2_w2", "f3_w1\nf3_w2"
#         ]
        
#         threads = [
#             threading.Thread(target=upload_worker, args=(c, f"t{i}.txt"))
#             for i, c in enumerate(file_contents)
#         ]
        
#         for t in threads: t.start()
#         for t in threads: t.join()
        
#         assert len(errors) == 0
#         with app.app_context():
#             # 验证数据库是否准确接收了 6 个单词
#             assert Word.query.count() == 6

#     def test_error_recovery_flow(self, test_client):
#         """TC_FLOW_004: 异常恢复流程（失败重试机制测试）"""
#         # 1. 上传
#         data = {'file': (BytesIO(b"recovery"), 'test.txt')}
#         test_client.post('/api/upload', data=data)
        
#         with app.app_context():
#             w = Word.query.filter_by(english='recovery').first()
#             assert w is not None
#             word_id = w.id

#         # 2. 模拟失败
#         with patch('app.get_translation') as mock_trans:
#             mock_trans.side_effect = Exception("Service Down")
#             resp = test_client.post(f'/api/translate_word/{word_id}')
#             assert resp.status_code == 500
            
#             # 验证状态未被写脏
#             with app.app_context():
#                 w_retry = db.session.get(Word, word_id)
#                 assert w_retry is not None
#                 assert w_retry.chinese == '待翻译...'

#         # 3. 模拟恢复后成功
#         with patch('app.get_translation') as mock_trans:
#             mock_trans.return_value = "恢复成功"
#             test_client.post(f'/api/translate_word/{word_id}')
#             with app.app_context():
#                 w_final = db.session.get(Word, word_id)
#                 assert w_final is not None
#                 assert w_final.chinese == "恢复成功"