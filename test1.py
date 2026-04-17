import streamlit as st
import json
import os
import spacy
from deep_translator import GoogleTranslator

# --- 1. 核心修复：确保模型加载无误 ---
@st.cache_resource
def get_nlp(lang_code):
    if lang_code == "en":
        try:
            return spacy.load("en_core_web_sm")
        except:
            os.system("python -m spacy download en_core_web_sm")
            return spacy.load("en_core_web_sm")
    else:
        try:
            return spacy.load("de_core_news_sm")
        except:
            os.system("python -m spacy download de_core_news_sm")
            return spacy.load("de_core_news_sm")

# 页面配置
st.set_page_config(page_title="经文精准解析助手", layout="centered")

class BibleWebApp:
    def __init__(self, dict_path="my_dict.json"):
        self.dict_path = dict_path
        if not os.path.exists(self.dict_path):
            with open(self.dict_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
        with open(self.dict_path, "r", encoding="utf-8") as f:
            self.my_dict = json.load(f)

    def save_dict(self):
        with open(self.dict_path, "w", encoding="utf-8") as f:
            json.dump(self.my_dict, f, ensure_ascii=False, indent=4)

app = BibleWebApp()

def clear_text():
    st.session_state["input_sentence"] = ""

st.title("📖 经文精准解析助手")
st.caption("修复版：支持英/德语自动识别与词性精准提取")

# --- 语言选择 ---
lang_option = st.radio("请先选择正确的输入语言:", ("英语 (English)", "德语 (Deutsch)"), horizontal=True)
source_code = "en" if "英语" in lang_option else "de"

# --- 输入框 ---
sentence = st.text_area(
    "请粘贴经文内容:", 
    placeholder="在此粘贴文本...",
    key="input_sentence",
    height=150
)

col1, col2 = st.columns([1, 5])
with col1:
    parse_btn = st.button("开始提取")
with col2:
    st.button("清除内容", on_click=clear_text)

if parse_btn:
    if sentence:
        with st.spinner('正在切换模型并精准解析...'):
            # 1. 确认加载正确的语言模型
            nlp = get_nlp(source_code)
            
            # 2. 原文回显
            st.markdown("---")
            st.subheader("📝 输入原文")
            st.info(sentence)

            # 3. 全句翻译
            translator = GoogleTranslator(source=source_code, target='zh-CN')
            full_zh = translator.translate(sentence)
            st.success(f"**中文意译：** {full_zh}")

            # 4. 执行 NLP 解析
            doc = nlp(sentence)
            verb_data = []
            adj_adv_data = []

            for token in doc:
                # 排除标点符号和空格
                if token.is_punct or token.is_space:
                    continue
                
                # 仅处理指定的词性
                if token.pos_ in ["VERB", "AUX", "ADJ", "ADV"]:
                    lemma = token.lemma_
                    
                    # 缓存逻辑
                    cache_key = f"{source_code}_{lemma}_zh"
                    if cache_key in app.my_dict:
                        zh_trans = app.my_dict[cache_key]
                    else:
                        try:
                            zh_trans = translator.translate(lemma)
                            app.my_dict[cache_key] = zh_trans
                        except:
                            zh_trans = "超时"

                    # 动词归类
                    if token.pos_ in ["VERB", "AUX"]:
                        verb_data.append({
                            "经文动词": token.text,
                            "动词原形": lemma,
                            "中文意思": zh_trans
                        })
                    # 形容词副词归类
                    elif token.pos_ in ["ADJ", "ADV"]:
                        pos_label = "形容词" if token.pos_ == "ADJ" else "副词"
                        adj_adv_data.append({
                            "经文原词": token.text,
                            "词类": pos_label,
                            "词原形": lemma,
                            "中文意思": zh_trans
                        })

            # 5. 显示表格
            if verb_data:
                st.subheader("🔍 动词对照表")
                st.table(verb_data)
            
            if adj_adv_data:
                st.subheader("🔍 形容词 & 副词对照表")
                st.table(adj_adv_data)
            
            app.save_dict()

            # 6. 生成笔记
            if verb_data or adj_adv_data:
                note_text = f"### 学习笔记\n**原文:** {sentence}\n**意译:** {full_zh}\n\n"
                # (此处省略 Markdown 拼接逻辑，保持与之前一致即可)
                st.download_button("下载本次笔记 (.md)", note_text, file_name="study_notes.md")
    else:
        st.warning("请先粘贴内容。")
