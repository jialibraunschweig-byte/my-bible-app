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
st.set_page_config(page_title="经文翻译助手", layout="centered")

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

st.title("📖 经文翻译助手")
st.caption("增强版：支持英/德语提取，德语模式下提供英语释义")

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
    parse_btn = st.button("开始翻译")
with col2:
    st.button("清除内容", on_click=clear_text)

if parse_btn:
    if sentence:
        with st.spinner('正在分析语法并翻译...'):
            # 1. 确认加载正确的语言模型
            nlp = get_nlp(source_code)
            
            # 2. 原文回显
            st.markdown("---")
            st.subheader("📝 输入原文")
            st.info(sentence)

            # 3. 初始化翻译器
            translator_zh = GoogleTranslator(source=source_code, target='zh-CN')
            # 如果是德语，额外增加德转英翻译器
            translator_en = GoogleTranslator(source='de', target='en') if source_code == "de" else None
            
            full_zh = translator_zh.translate(sentence)
            st.success(f"**中文意译：** {full_zh}")

            # 4. 执行 NLP 解析
            doc = nlp(sentence)
            verb_data = []
            adj_adv_data = []

            for token in doc:
                if token.is_punct or token.is_space:
                    continue
                
                if token.pos_ in ["VERB", "AUX", "ADJ", "ADV"]:
                    lemma = token.lemma_
                    
                    # 缓存与翻译逻辑
                    cache_key = f"{source_code}_{lemma}_trans"
                    if cache_key in app.my_dict:
                        trans_info = app.my_dict[cache_key]
                    else:
                        try:
                            zh_val = translator_zh.translate(lemma)
                            # 如果是德语，获取英语解释
                            en_val = translator_en.translate(lemma) if translator_en else None
                            trans_info = {"zh": zh_val, "en": en_val}
                            app.my_dict[cache_key] = trans_info
                        except:
                            trans_info = {"zh": "超时", "en": "超时"}

                    # 构建基础数据行
                    row_data = {
                        "原形": lemma,
                        "中文": trans_info["zh"]
                    }
                    # 如果有英语解释，加入行数据
                    if trans_info["en"]:
                        row_data["英语"] = trans_info["en"]

                    # 分类存入
                    if token.pos_ in ["VERB", "AUX"]:
                        v_row = {"经文动词": token.text}
                        v_row.update(row_data)
                        verb_data.append(v_row)
                    elif token.pos_ in ["ADJ", "ADV"]:
                        pos_label = "形容词" if token.pos_ == "ADJ" else "副词"
                        a_row = {"经文原词": token.text, "词类": pos_label}
                        a_row.update(row_data)
                        adj_adv_data.append(a_row)

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
                # 简单拼接逻辑
                if verb_data:
                    note_text += "#### 动词表\n" + str(verb_data) + "\n"
                if adj_adv_data:
                    note_text += "#### 形容/副词表\n" + str(adj_adv_data) + "\n"
                
                st.download_button("下载本次笔记 (.md)", note_text, file_name="study_notes.md")
    else:
        st.warning("请先粘贴内容。")
