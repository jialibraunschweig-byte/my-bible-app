import streamlit as st
import json
import os
import spacy
from deep_translator import GoogleTranslator

# --- 1. 模型加载 ---
@st.cache_resource
def get_nlp(lang_code):
    model_name = "en_core_web_sm" if lang_code == "en" else "de_core_news_sm"
    try:
        return spacy.load(model_name)
    except:
        os.system(f"python -m spacy download {model_name}")
        return spacy.load(model_name)

# 页面配置
st.set_page_config(page_title="经文全解析 - 增强版", layout="centered")

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

st.title("📖 经文词汇与固定短语解析")
st.caption("修复版：针对 zugrunde gehen 等德语固定搭配进行了深度优化")

# --- 语言选择 ---
lang_option = st.radio("请选择输入语言:", ("德语 (Deutsch)", "英语 (English)"), horizontal=True)
source_code = "de" if "德语" in lang_option else "en"
target_aux_code = "en" if source_code == "de" else "de"
aux_col_name = "英语解释" if source_code == "de" else "德语解释"

sentence = st.text_area("请粘贴经文内容:", key="input_sentence", height=150)

col1, col2 = st.columns([1, 5])
with col1:
    parse_btn = st.button("开始提取")
with col2:
    st.button("清除内容", on_click=clear_text)

# 德语常见分离前缀
GERMAN_PREFIXES = {"ab", "an", "auf", "aus", "bei", "ein", "empor", "entgegen", "fest", "fort", "her", "hin", "los", "nach", "nieder", "vor", "weg", "weiter", "zu", "zurück", "zusammen"}

if parse_btn:
    if sentence:
        with st.spinner('深度解析句法结构中...'):
            nlp = get_nlp(source_code)
            doc = nlp(sentence)
            
            translator_zh = GoogleTranslator(source=source_code, target='zh-CN')
            translator_aux = GoogleTranslator(source=source_code, target=target_aux_code)
            
            full_zh = translator_zh.translate(sentence)
            st.success(f"**中文意译：** {full_zh}")

            verb_data, adj_adv_data, noun_data, phrase_data = [], [], [], []
            
            # --- 核心改进：更强力的固定搭配提取逻辑 ---
            processed_phrases = set() # 用于去重

            for token in doc:
                # 当遇到动词或特定补足语时进行关联
                if token.pos_ in ["VERB", "AUX"]:
                    phrase_tokens = [token]
                    
                    # 检索所有与动词相关的补足语 (包括 zugrunde, in Kauf 等)
                    for child in token.children:
                        # 德语中 zugrunde 经常被标记为 advmod 或 compound
                        if child.dep_ in ["compound", "advmod", "obj", "obl", "xcomp", "ng"]:
                            # 过滤：只提取短小的、有实际意义的词组 (长度 < 4)
                            if child.pos_ in ["NOUN", "ADV", "ADP", "PART"]:
                                sub_tree = [t for t in child.subtree if not t.is_punct]
                                if 0 < len(sub_tree) < 4:
                                    phrase_tokens.extend(sub_tree)
                    
                    if len(phrase_tokens) > 1:
                        # 按语序排序并去重
                        phrase_tokens = sorted(list(set(phrase_tokens)), key=lambda x: x.i)
                        phrase_text = " ".join([t.text for t in phrase_tokens])
                        
                        # 特殊过滤：排除包含 "nicht" 的简单否定，除非它是搭配的一部分
                        if phrase_text.lower() not in processed_phrases:
                            cache_key = f"{source_code}_{phrase_text}_idiom_v8"
                            if cache_key not in app.my_dict:
                                try:
                                    zh_val = translator_zh.translate(phrase_text)
                                    aux_val = translator_aux.translate(phrase_text)
                                    app.my_dict[cache_key] = {"zh": zh_val, "aux": aux_val}
                                except:
                                    app.my_dict[cache_key] = {"zh": "超时", "aux": "超时"}
                            
                            p_trans = app.my_dict[cache_key]
                            phrase_data.append({"固定短语": phrase_text, "中文意思": p_trans["zh"], aux_col_name: p_trans["aux"]})
                            processed_phrases.add(phrase_text.lower())

            # --- 单词提取逻辑 ---
            particles_map = {} 
            if source_code == "de":
                for token in doc:
                    if token.dep_ == "svp" and token.text.lower() in GERMAN_PREFIXES:
                        if token.head.i not in particles_map: particles_map[token.head.i] = []
                        particles_map[token.head.i].append(token.text.lower())

            for token in doc:
                if token.is_punct or token.is_space or token.dep_ == "svp" or token.pos_ in ["PRON", "DET"]:
                    continue
                
                if token.pos_ in ["VERB", "AUX", "ADJ", "ADV", "NOUN", "PROPN"]:
                    lemma = token.lemma_
                    original_text = token.text

                    if source_code == "de" and token.i in particles_map:
                        pref = "".join(particles_map[token.i])
                        if not lemma.startswith(pref): lemma = pref + lemma
                        original_text = f"{token.text} ... {pref}"

                    cache_key = f"{source_code}_{lemma}_final_v8" 
                    if cache_key not in app.my_dict:
                        try:
                            zh_val = translator_zh.translate(lemma)
                            aux_val = translator_aux.translate(lemma)
                            app.my_dict[cache_key] = {"zh": zh_val, "aux": aux_val}
                        except:
                            app.my_dict[cache_key] = {"zh": "超时", "aux": "超时"}
                    
                    t_trans = app.my_dict[cache_key]
                    row = {"词原形": lemma, "中文意思": t_trans["zh"], aux_col_name: t_trans["aux"]}

                    if token.pos_ in ["VERB", "AUX"]: verb_data.append({"经文动词": original_text, **row})
                    elif token.pos_ in ["ADJ", "ADV"]: adj_adv_data.append({"经文原词": token.text, "词类": "形/副", **row})
                    elif token.pos_ in ["NOUN", "PROPN"]: noun_data.append({"经文名词": token.text, **row})

            # 界面展示
            if phrase_data:
                st.subheader("🚀 固定短语/搭配表")
                st.table(phrase_data)
            if verb_data:
                st.subheader("🔍 动词表")
                st.table(verb_data)
            if noun_data:
                st.subheader("🔍 名词表")
                st.table(noun_data)
            if adj_adv_data:
                st.subheader("🔍 形容词/副词表")
                st.table(adj_adv_data)
            
            app.save_dict()
    else:
        st.warning("请先粘贴内容。")
