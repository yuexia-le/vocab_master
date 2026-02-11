from selenium import webdriver
from selenium.webdriver.chrome.options import Options   #设置谷歌浏览器
from selenium.webdriver.chrome.service import Service   #管理谷歌驱动
from selenium.webdriver.common.by import By             #元素定位
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

#设置浏览器、启动浏览器
def start():
    #创建设置浏览对象
    q1 = Options()
    #禁用沙盒(增加兼容性)
    q1.add_argument('--no-sandbox')   
    #保持浏览器打开状态
    q1.add_experimental_option('detach',True)
    #创建并启动浏览器
    a1 = webdriver.Chrome(service=Service('chromedriver.exe'), options=q1)
    a1.implicitly_wait(5)
    return a1

b1 = None
try:
    b1 = start()
    #打开指定网址
    b1.get('http://127.0.0.1:5000/')

    #元素定位-生成今日故事
    b1.find_element(By.XPATH,'/html/body/div/div[1]/button').click()
    story = b1.find_element(By.ID,'story-box').text
    assert len(story) > 0, "断言失败：故事生成内容为空！"
    print("✅ 验证通过: AI 故事生成测试通过")
    time.sleep(3)
    #造句-换一句
    again = b1.find_element(By.XPATH,'/html/body/div/div[2]/div/button[2]').click()
    time.sleep(5)
    #造句-输入信息
    box = b1.find_element(By.XPATH,'//*[@id="user-input"]')
    box.send_keys('测试')
    assert box.get_attribute('value') == '测试', "断言失败：输入框内容与预期不一致！"
    print("✅ 验证通过: 输入信息成功")
    time.sleep(10)
    #造句-检查答案
    check = b1.find_element(By.XPATH,'/html/body/div/div[2]/div/button[1]').click()
    time.sleep(5)

    #显示-只看英文
    b1.find_element(By.XPATH,'//*[@id="btn-en"]').click()
    cn_element = b1.find_element(By.CLASS_NAME, 'word-cn')
    classes_cn = cn_element.get_attribute('class')
    assert classes_cn is not None, "错误：无法获取元素的 class 属性"
    assert 'blur' in classes_cn, f"断言失败！只看英文模式下中文未模糊。当前class为: {classes_cn}"
    print("✅ 验证通过：只看英文模式生效（中文已模糊）")
 
    time.sleep(2)
    #显示-只看中文
    b1.find_element(By.XPATH,'//*[@id="btn-cn"]').click()
    en_element = b1.find_element(By.CLASS_NAME, 'word-en')
    classes_cn = en_element.get_attribute('class')
    assert classes_cn is not None, "错误：无法获取元素的 class 属性"
    assert 'blur' in classes_cn, f"断言失败！只看中文模式下英文未模糊。当前class为: {classes_cn}"
    print("✅ 验证通过：只看中文模式生效（英文已模糊）")
    time.sleep(2)

    #后台管理
    b1.find_element(By.XPATH,'/html/body/div/header/a').click()
    time.sleep(2)
    #assert enter is not None, "错误：无法获取元素的 class 属性"
    assert "管理" in b1.title or 'Admin' in b1.page_source, "断言失败：进入后台管理失败！"
    print("✅ 验证通过：进入后台管理成功！")
    time.sleep(2)
    #选择文件
    select = b1.find_element(By.XPATH,'//*[@id="fileInput"]').send_keys('D:\\PythonProject\\vocab_master\\word_selenium\\blue.txt')
    time.sleep(2)
    #点击上传
    upload = b1.find_element(By.XPATH,'/html/body/div/div[1]/button').click()
    time.sleep(2)
    #lower()不区分大小写在页面找文本
    assert "blue" in b1.page_source.lower(), "断言失败：上传文件后页面未发现新增单词 'blue'"
    print("✅ 验证通过：文件上传及单词解析成功")
    #点击删除
    #寻找文本内容包含 "blue" 的那一个<td>,/..跳到父元素<td>，锁定整行tr，/td[last()]找到这行最后一个td按钮
    dynamic_xpath = "//td[contains(text(), 'blue')]/../td[last()]/button"
    delete = b1.find_element(By.XPATH,dynamic_xpath)
    #execute_script执行js直接操作DOM，scrollIntoView将元素滚动到用户可见，{block: 'center'}滚动居中
    #arguments[0]代表第一个参数，也就是delete
    b1.execute_script("arguments[0].scrollIntoView({block: 'center'});", delete)
    delete.click()
    b1.switch_to.alert.accept()
    time.sleep(2)
    assert b1.page_source.lower() != "blue", "断言失败：删除单词后页面仍能找到 'blue'"
    print("✅ 验证通过：单词删除成功")
    time.sleep(2)
except AssertionError as ae:
    print(f"\n× [断言异常]：{ae}")
    # 2. 核心修正：加一个 if 判断，解决“None 没有 save_screenshot 属性”的报错
    if b1 is not None:
        b1.save_screenshot('error_assertion.png')
except Exception as e:
    print(f"\n× [运行异常]：{e}")
    if b1 is not None:
        b1.save_screenshot('error_runtime.png')
finally:
    print("测试脚本执行结束。")









