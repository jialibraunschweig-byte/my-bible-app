import streamlit as st
import json
import os
import spacy
from deep_translator import GoogleTranslator

# --- 1. 模型加载 ---
@st.cache_resource
def load_nlp():
    return spacy.load("de_core_news_sm")

nlp = load_nlp()

# 页面配置
st.set_page_config(page_title="德语动词解析助手", layout="centered")

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

# 清空输入框的逻辑
def clear_text():
    st.session_state["input_sentence"] = ""

st.title("📖 德语经文：动词精简解析")
st.caption("自动提取动词原形并翻译，支持原文显示与一键清空")

# --- 输入框 ---
sentence = st.text_area(
    "请粘贴德语经文:", 
    placeholder="例如：Denn Gott hat die Welt so sehr geliebt...",
    key="input_sentence",
    height=150
)

# 按钮布局
col1, col2 = st.columns([1, 5])
with col1:
    parse_btn = st.button("开始提取")
with col2:
    st.button("清除内容", on_click=clear_text)

if parse_btn:
    if sentence:
        with st.spinner('正在分析语法并翻译...'):
            # 1. 完整显示原文 (新增部分)
            st.markdown("---")
            st.subheader("📝 输入原文")
            st.info(sentence)

            # 2. 全句意译
            full_trans = app.translator.translate(sentence)
            st.success(f"**全句意译：** {full_trans}")

            # 3. NLP 动词提取
            doc = nlp(sentence)
            table_data = []

            for token in doc:
                if token.pos_ in ["VERB", "AUX"]:
                    lemma = token.lemma_
                    
                    if lemma in app.my_dict:
                        trans = app.my_dict[lemma]
                    else:
                        try:
                            trans = app.translator.translate(lemma)
                            app.my_dict[lemma] = trans
                        except:
                            trans = "超时"

                    table_data.append({
                        "经文动词": token.text,
                        "动词原形": lemma,
                        "对应汉语": trans
                    })

            # 4. 显示动词表格
            if table_data:
                st.subheader("🔍 动词对照表")
                st.table(table_data)
                app.save_dict()

                # 5. 生成笔记
                note_text = f"### 德语学习笔记\n**原文:** {sentence}\n**意译:** {full_trans}\n\n| 经文动词 | 动词原形 | 对应汉语 |\n|---|---|---|\n"
                for row in table_data:
                    note_text += f"| {row['经文动词']} | {row['动词原形']} | {row['对应汉语']} |\n"
                
                st.download_button("下载本次笔记 (.md)", note_text, file_name="german_verbs.md")
            else:
                st.info("在该段文本中未识别到动词。")
    else:
        st.warning("请先粘贴内容。")
