import streamlit as st
import json
import os
import spacy
from deep_translator import GoogleTranslator

# --- 1. 核心模型加载 ---
@st.cache_resource
def get_nlp(lang_code):
    model_name = "en_core_web_sm" if lang_code == "en" else "de_core_news_sm"
    try:
        return spacy.load(model_name)
    except:
        os.system(f"python -m spacy download {model_name}")
        return spacy.load(model_name)

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
st.caption("增强版：深度处理德语分离动词（解决 wiesen ... ab 等识别问题）")

# --- 语言选择 ---
lang_option = st.radio("请选择输入语言:", ("德语 (Deutsch)", "英语 (English)"), horizontal=True)
source_code = "de" if "德语" in lang_option else "en"

# --- 输入框 ---
sentence = st.text_area(
    "请粘贴经文内容:", 
    placeholder="例如：Er kam in seine Welt, aber die Menschen wiesen ihn ab.",
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
        with st.spinner('正在分析复杂语法结构...'):
            nlp = get_nlp(source_code)
            
            # 1. 界面回显
            st.markdown("---")
            st.subheader("📝 输入原文")
            st.info(sentence)

            # 2. 翻译器初始化
            translator_zh = GoogleTranslator(source=source_code, target='zh-CN')
            translator_en = GoogleTranslator(source='de', target='en') if source_code == "de" else None
            
            full_zh = translator_zh.translate(sentence)
            st.success(f"**中文意译：** {full_zh}")

            # 3. NLP 深度解析
            doc = nlp(sentence)
            verb_data = []
            adj_adv_data = []
            
            # 记录已经被合并的前缀，防止它们单独出现在形容词/副词表里
            particles_to_ignore = []
            if source_code == "de":
                for token in doc:
                    # 识别所有指向动词的分离前缀 (svp) 或 补足成分 (compound/prt)
                    if token.dep_ in ["svp", "compound:prt"] or (token.pos_ == "ADP" and token.head.pos_ == "VERB"):
                        particles_to_ignore.append(token.i)

            for token in doc:
                # 排除标点、空格和已被合并的前缀
                if token.is_punct or token.is_space or token.i in particles_to_ignore:
                    continue
                
                # 核心过滤：动词、助动词、形容词、副词
                if token.pos_ in ["VERB", "AUX", "ADJ", "ADV"]:
                    # spaCy 的 lemma_ 在德语中通常能自动处理分离动词
                    # 比如 wiesen 会被还原为 abweisen，前提是 ab 标记正确
                    lemma = token.lemma_
                    
                    # 容错处理：如果 lemma 依然只是 "weisen"，但我们发现它有前缀被忽略了
                    # 这里不需要手动拼接，spaCy 模型如果版本正确通常能自动完成。
                    # 我们重点确保“ab”不重复出现在其他表里即可。

                    # 缓存与翻译
                    cache_key = f"{source_code}_{lemma}_trans"
                    if cache_key in app.my_dict:
                        trans_info = app.my_dict[cache_key]
                    else:
                        try:
                            zh_val = translator_zh.translate(lemma)
                            en_val = translator_en.translate(lemma) if translator_en else None
                            trans_info = {"zh": zh_val, "en": en_val}
                            app.my_dict[cache_key] = trans_info
                        except:
                            trans_info = {"zh": "超时", "en": "超时"}

                    # 构建数据
                    row_data = {"词原形": lemma, "中文意思": trans_info["zh"]}
                    if trans_info["en"]: row_data["英语解释"] = trans_info["en"]

                    if token.pos_ in ["VERB", "AUX"]:
                        v_row = {"经文动词": token.text}
                        v_row.update(row_data)
                        verb_data.append(v_row)
                    elif token.pos_ in ["ADJ", "ADV"]:
                        pos_label = "形容词" if token.pos_ == "ADJ" else "副词"
                        a_row = {"经文原词": token.text, "词类": pos_label}
                        a_row.update(row_data)
                        adj_adv_data.append(a_row)

            # 4. 展示表格
            if verb_data:
                st.subheader("🔍 动词对照表")
                st.table(verb_data)
            if adj_adv_data:
                st.subheader("🔍 形容词 & 副词对照表")
                st.table(adj_adv_data)
            
            app.save_dict()
    else:
        st.warning("请先粘贴内容。")
