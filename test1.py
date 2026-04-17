import streamlit as st
import json
import os
import spacy
from deep_translator import GoogleTranslator

# --- 1. 模型加载 (针对 Streamlit 优化) ---
@st.cache_resource
def load_nlp():
    try:
        return spacy.load("de_core_news_sm")
    except:
        os.system("python -m spacy download de_core_news_sm")
        return spacy.load("de_core_news_sm")

nlp = load_nlp()

# 页面配置
st.set_page_config(page_title="德语动词解析", layout="centered")

class BibleWebApp:
    def __init__(self, dict_path="my_dict.json"):
        self.dict_path = dict_path
        if not os.path.exists(self.dict_path):
            with open(self.dict_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

        with open(self.dict_path, "r", encoding="utf-8") as f:
            self.my_dict = json.load(f)

        self.translator = GoogleTranslator(source='de', target='zh-CN')

    def save_dict(self):
        with open(self.dict_path, "w", encoding="utf-8") as f:
            json.dump(self.my_dict, f, ensure_ascii=False, indent=4)

app = BibleWebApp()

st.title("📖 德语经文：动词精简解析")
st.caption("自动提取动词原型并翻译，去除冗余信息")

sentence = st.text_area("请粘贴德语经文:", placeholder="输入德语文本...")

if st.button("开始提取"):
    if sentence:
        with st.spinner('解析中...'):
            # 1. 全句翻译
            full_trans = app.translator.translate(sentence)
            st.success(f"**全句意译：** {full_trans}")

            # 2. NLP 动词提取
            doc = nlp(sentence)
            table_data = []

            for token in doc:
                # 仅筛选动词和助动词
                if token.pos_ in ["VERB", "AUX"]:
                    lemma = token.lemma_
                    
                    # 查词典或在线翻译
                    if lemma in app.my_dict:
                        trans = app.my_dict[lemma]
                    else:
                        try:
                            trans = app.translator.translate(lemma)
                            app.my_dict[lemma] = trans
                        except:
                            trans = "超时"

                    # 核心修改：只保留三列
                    table_data.append({
                        "经文动词": token.text,
                        "动词原形": lemma,
                        "对应汉语": trans
                    })

            # 3. 显示精简表格
            if table_data:
                st.subheader("🔍 动词对照表")
                st.table(table_data)
                
                app.save_dict()

                # 4. 导出笔记 (Markdown 格式)
                note_text = f"### 德语动词学习笔记\n**原文:** {sentence}\n\n| 经文动词 | 动词原形 | 对应汉语 |\n|---|---|---|\n"
                for row in table_data:
                    note_text += f"| {row['经文动词']} | {row['动词原形']} | {row['对应汉语']} |\n"
                
                st.download_button("下载 Markdown 笔记", note_text, file_name="verbs_study.md")
            else:
                st.info("未发现动词。")
    else:
        st.warning("内容不能为空。")
