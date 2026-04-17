import streamlit as st
import json
import os
import spacy
from deep_translator import GoogleTranslator

# --- 1. 模型加载 (支持德语和英语) ---
@st.cache_resource
def load_models():
    models = {}
    # 加载德语模型
    try:
        models["de"] = spacy.load("de_core_news_sm")
    except:
        os.system("python -m spacy download de_core_news_sm")
        models["de"] = spacy.load("de_core_news_sm")
    
    # 加载英语模型
    try:
        models["en"] = spacy.load("en_core_web_sm")
    except:
        os.system("python -m spacy download en_core_web_sm")
        models["en"] = spacy.load("en_core_web_sm")
    return models

nlp_models = load_models()

# 页面配置
st.set_page_config(page_title="经文词汇解析助手", layout="centered")

class BibleWebApp:
    def __init__(self, dict_path="my_dict.json"):
        self.dict_path = dict_path
        if not os.path.exists(self.dict_path):
            with open(self.dict_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

        with open(self.dict_path, "r", encoding="utf-8") as f:
            self.my_dict = json.load(f)

    def get_translator(self, source_lang):
        return GoogleTranslator(source=source_lang, target='zh-CN')

    def save_dict(self):
        with open(self.dict_path, "w", encoding="utf-8") as f:
            json.dump(self.my_dict, f, ensure_ascii=False, indent=4)

app = BibleWebApp()

def clear_text():
    st.session_state["input_sentence"] = ""

st.title("📖 经文词汇解析助手")
st.caption("支持英/德语动词、形容词及副词提取与中文对照")

# --- 语言选择 ---
lang_option = st.radio("请选择输入语言:", ("德语 (Deutsch)", "英语 (English)"), horizontal=True)
source_code = "de" if "德语" in lang_option else "en"

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
        with st.spinner('正在分析语法并翻译...'):
            # 1. 原文回显
            st.markdown("---")
            st.subheader("📝 输入原文")
            st.info(sentence)

            # 2. 全句翻译
            translator = app.get_translator(source_code)
            full_zh = translator.translate(sentence)
            st.success(f"**中文意译：** {full_zh}")

            # 3. NLP 解析
            nlp = nlp_models[source_code]
            doc = nlp(sentence)
            
            verb_data = []      # 存储动词
            adj_adv_data = []   # 存储形容词和副词

            for token in doc:
                # 提取原型
                lemma = token.lemma_
                
                # 翻译缓存逻辑
                cache_key = f"{source_code}_{lemma}_zh"
                if cache_key in app.my_dict:
                    zh_trans = app.my_dict[cache_key]
                else:
                    try:
                        zh_trans = translator.translate(lemma)
                        app.my_dict[cache_key] = zh_trans
                    except:
                        zh_trans = "超时"

                # 分类存入表格
                # 动词类
                if token.pos_ in ["VERB", "AUX"]:
                    verb_data.append({
                        "经文动词": token.text,
                        "动词原形": lemma,
                        "中文意思": zh_trans
                    })
                # 形容词和副词类
                elif token.pos_ in ["ADJ", "ADV"]:
                    pos_label = "形容词" if token.pos_ == "ADJ" else "副词"
                    adj_adv_data.append({
                        "经文原词": token.text,
                        "词类": pos_label,
                        "词原形": lemma,
                        "中文意思": zh_trans
                    })

            # 4. 显示结果表格
            # 动词表
            if verb_data:
                st.subheader("🔍 动词对照表")
                st.table(verb_data)
            
            # 形容词/副词表
            if adj_adv_data:
                st.subheader("🔍 形容词 & 副词对照表")
                st.table(adj_adv_data)
            
            app.save_dict()

            # 5. 生成笔记 (包含两个表格)
            if verb_data or adj_adv_data:
                note_text = f"### 学习笔记 ({lang_option})\n**原文:** {sentence}\n**中文:** {full_zh}\n\n"
                
                if verb_data:
                    note_text += "#### 动词部分\n| 经文动词 | 动词原形 | 中文意思 |\n|---|---|---|\n"
                    for row in verb_data:
                        note_text += f"| {row['经文动词']} | {row['动词原形']} | {row['中文意思']} |\n"
                
                if adj_adv_data:
                    note_text += "\n#### 形容词/副词部分\n| 经文原词 | 词类 | 词原形 | 中文意思 |\n|---|---|---|---|\n"
                    for row in adj_adv_data:
                        note_text += f"| {row['经文原词']} | {row['词类']} | {row['词原形']} | {row['中文意思']} |\n"
                
                st.download_button("下载本次笔记 (.md)", note_text, file_name="scripture_study_full.md")
            else:
                st.info("未识别到指定的词类。")
    else:
        st.warning("请先粘贴内容。")
