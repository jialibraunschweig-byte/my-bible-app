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
st.set_page_config(page_title="德语固定搭配精准解析", layout="centered")

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

st.title("📖 经文翻译器")
st.caption("核心改进：自动还原动词原形，精准识别固定搭配")

lang_option = st.radio("请选择输入语言:", ("德语 (Deutsch)", "英语 (English)"), horizontal=True)
source_code = "de" if "德语" in lang_option else "en"
target_aux_code = "en" if source_code == "de" else "de"
aux_col_name = "英语解释" if source_code == "de" else "德语解释"

sentence = st.text_area("请粘贴经文:", key="input_sentence", height=120)

col1, col2 = st.columns([1, 5])
with col1:
    parse_btn = st.button("开始翻译")
with col2:
    st.button("清除内容", on_click=clear_text)

GERMAN_PREFIXES = {"ab", "an", "auf", "aus", "bei", "ein", "empor", "entgegen", "fest", "fort", "her", "hin", "los", "nach", "nieder", "vor", "weg", "weiter", "zu", "zurück", "zusammen"}

if parse_btn:
    if sentence:
        with st.spinner('正在分析句法结构并还原词形...'):
            nlp = get_nlp(source_code)
            doc = nlp(sentence)
            
            translator_zh = GoogleTranslator(source=source_code, target='zh-CN')
            translator_aux = GoogleTranslator(source=source_code, target=target_aux_code)
            
            full_zh = translator_zh.translate(sentence)
            st.success(f"**中文意译：** {full_zh}")

            verb_data, adj_adv_data, noun_data, phrase_data = [], [], [], []
            processed_phrases = set()

            # --- 核心改进：短语原形化提取 ---
            for token in doc:
                if token.pos_ in ["VERB", "AUX"]:
                    # 尝试寻找介词和关联的名词
                    for child in token.children:
                        if child.dep_ in ["prep", "obl", "obj"]:
                            # 捕获介词（如 zu）
                            prep_word = child.text if child.pos_ == "ADP" else ""
                            # 捕获该分支下的名词原形（如 Expedition）
                            content_words = [t.lemma_ for t in child.subtree if t.pos_ in ["NOUN", "PROPN"]]
                            
                            if prep_word or content_words:
                                # 构造原形搭配：例如 "zu etwas aufbrechen"
                                if prep_word:
                                    display_phrase = f"{prep_word} etwas {token.lemma_}"
                                else:
                                    display_phrase = f"{token.lemma_} ({' '.join(content_words)})"
                                
                                if display_phrase.lower() not in processed_phrases:
                                    cache_key = f"{source_code}_{display_phrase}_idiom_final_v12"
                                    if cache_key not in app.my_dict:
                                        try:
                                            # 使用原形进行翻译，准确率大幅提升
                                            app.my_dict[cache_key] = {
                                                "zh": translator_zh.translate(display_phrase),
                                                "aux": translator_aux.translate(display_phrase)
                                            }
                                        except:
                                            app.my_dict[cache_key] = {"zh": "超时", "aux": "超时"}
                                    
                                    res = app.my_dict[cache_key]
                                    phrase_data.append({"固定搭配 (原形)": display_phrase, "中文意思": res["zh"], aux_col_name: res["aux"]})
                                    processed_phrases.add(display_phrase.lower())

            # --- 基础单词提取 ---
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
                    
                    cache_key = f"{source_code}_{lemma}_v12"
                    if cache_key not in app.my_dict:
                        try:
                            app.my_dict[cache_key] = {
                                "zh": translator_zh.translate(lemma),
                                "aux": translator_aux.translate(lemma)
                            }
                        except:
                            app.my_dict[cache_key] = {"zh": "错误", "aux": "错误"}
                    
                    row = {"词原形": lemma, "中文意思": app.my_dict[cache_key]["zh"], aux_col_name: app.my_dict[cache_key]["aux"]}
                    if token.pos_ in ["VERB", "AUX"]: verb_data.append({"经文动词": original_text, **row})
                    elif token.pos_ in ["ADJ", "ADV"]: adj_adv_data.append({"经文原词": token.text, "词类": "形/副词", **row})
                    elif token.pos_ in ["NOUN", "PROPN"]: noun_data.append({"经文名词": token.text, **row})

            # 展示
            if phrase_data:
                st.subheader("🚀 固定搭配提取 (还原原形)")
                st.table(phrase_data)
            if verb_data: st.subheader("🔍 动词表"); st.table(verb_data)
            if noun_data: st.subheader("🔍 名词表"); st.table(noun_data)
            if adj_adv_data: st.subheader("🔍 形容词/副词表"); st.table(adj_adv_data)
            app.save_dict()
