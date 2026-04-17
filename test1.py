import streamlit as st
import json
import os
import spacy
from deep_translator import GoogleTranslator

# --- 1. 模型加载 (针对 Streamlit 优化) ---
@st.cache_resource
def load_nlp():
    # 只要 requirements.txt 里写了那个 .whl 链接，这里直接加载即可
    return spacy.load("de_core_news_sm")

# 初始化 NLP 模型
nlp = load_nlp()

# 页面配置
st.set_page_config(page_title="德语动词解析助手", layout="centered")

class BibleWebApp:
    def __init__(self, dict_path="my_dict.json"):
        self.dict_path = dict_path
        # 初始化词典文件，如果不存在则创建一个空的
        if not os.path.exists(self.dict_path):
            with open(self.dict_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

        # 读取本地词典缓存
        with open(self.dict_path, "r", encoding="utf-8") as f:
            self.my_dict = json.load(f)

        # 初始化翻译引擎
        self.translator = GoogleTranslator(source='de', target='zh-CN')

    def save_dict(self):
        # 将更新后的词典存入 JSON 文件
        with open(self.dict_path, "w", encoding="utf-8") as f:
            json.dump(self.my_dict, f, ensure_ascii=False, indent=4)

# --- 2. 初始化应用实例 ---
app = BibleWebApp()

st.title("📖 德语经文：动词精简解析")
st.caption("自动提取动词原形并翻译，生成的笔记可直接用于学习")

# 输入框
sentence = st.text_area("请粘贴德语经文:", placeholder="例如：Denn Gott hat die Welt so sehr geliebt...")

if st.button("开始提取动词"):
    if sentence:
        with st.spinner('正在分析语法并翻译...'):
            # 1. 全句意译
            full_trans = app.translator.translate(sentence)
            st.success(f"**全句意译：** {full_trans}")

            # 2. NLP 动词提取
            doc = nlp(sentence)
            table_data = []

            for token in doc:
                # 核心筛选：只保留动词 (VERB) 和 助动词 (AUX)
                if token.pos_ in ["VERB", "AUX"]:
                    lemma = token.lemma_  # 获取动词原形
                    
                    # 优先查本地词典，没有再调翻译接口
                    if lemma in app.my_dict:
                        trans = app.my_dict[lemma]
                    else:
                        try:
                            # 翻译动词原形（学习动词最有效的方法）
                            trans = app.translator.translate(lemma)
                            app.my_dict[lemma] = trans
                        except:
                            trans = "超时"

                    # 构建精简表格：只包含三列
                    table_data.append({
                        "经文动词": token.text,
                        "动词原形": lemma,
                        "对应汉语": trans
                    })

            # 3. 显示结果
            if table_data:
                st.subheader("🔍 动词对照表")
                st.table(table_data)
                
                # 更新本地词典
                app.save_dict()

                # 4. 生成 Markdown 笔记
                note_text = f"### 德语学习笔记\n**原文:** {sentence}\n**意译:** {full_trans}\n\n| 经文动词 | 动词原形 | 对应汉语 |\n|---|---|---|\n"
                for row in table_data:
                    note_text += f"| {row['经文动词']} | {row['动词原形']} | {row['对应汉语']} |\n"
                
                st.download_button("下载本次笔记 (.md)", note_text, file_name="german_verbs.md")
            else:
                st.info("在该段文本中未识别到动词。")
    else:
        st.warning("请先粘贴内容。")
