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
st.set_page_config(page_title="德语经文精准解析器", layout="wide")

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

# --- 2. 核心翻译逻辑 ---
def smart_translate(text, pos, source_lang="de"):
    try:
        if source_lang == "de":
            if pos == "VERB":
                query = f"Bedeutung vom Verb '{text}' im Sinne von Gesetz oder Handlung"
            elif pos == "PHRASE":
                query = f"Was bedeutet die Redewendung '{text}'?"
            else:
                query = text
            
            raw_res = GoogleTranslator(source='de', target='zh-CN').translate(query)
            return raw_res.replace("的意思是", "").replace("含义是", "").split("：")[-1].strip()
        else:
            return GoogleTranslator(source=source_lang, target='zh-CN').translate(text)
    except:
        return "翻译超时"

def clear_text():
    st.session_state["input_sentence"] = ""

# --- 3. 过滤列表：排除物主代词 (Possessive Pronouns) ---
# 这些词虽然常被标记为 ADJ，但实际上是代词性质
EXCLUDE_PRONOMINAL_ADJS = {
    "mein", "dein", "sein", "ihr", "unser", "euer", "ihre", 
    "meine", "deine", "seine", "unsere", "eure", "ihrer", "ihres"
}

st.title("📖 德语经文精准解析器")
st.info("💡 已优化：形容词表中将不再显示物主代词（如 deine, eure, ihre 等）。")

# --- UI 布局 ---
lang_option = st.radio("选择语言:", ("德语 (Deutsch)", "英语 (English)"), horizontal=True)
source_code = "de" if "德语" in lang_option else "en"
target_aux_code = "en" if source_code == "de" else "de"

sentence = st.text_area("请粘贴德语内容:", key="input_sentence", height=150)

col1, col2 = st.columns([1, 5])
with col1:
    parse_btn = st.button("开始深度解析")
with col2:
    st.button("清除内容", on_click=clear_text)

GERMAN_PREFIXES = {"ab", "an", "auf", "aus", "bei", "ein", "empor", "entgegen", "fest", "fort", "her", "hin", "los", "nach", "nieder", "vor", "weg", "weiter", "zu", "zurück", "zusammen", "um"}

if parse_btn and sentence:
    with st.spinner('正在分析语法并过滤无关词汇...'):
        nlp = get_nlp(source_code)
        doc = nlp(sentence)
        
        full_zh = GoogleTranslator(source=source_code, target='zh-CN').translate(sentence)
        st.success(f"**全句意译：** {full_zh}")

        verb_data, adj_adv_data, noun_data, phrase_data = [], [], [], []
        processed_keys = set()

        # 预处理可分前缀
        particles_map = {}
        for token in doc:
            if token.dep_ == "svp":
                particles_map[token.head.i] = token.text.lower()

        for token in doc:
            # 过滤掉标点、代词、冠词、连词等基础结构词
            if token.is_punct or token.is_space or token.pos_ in ["PRON", "DET", "CONJ", "SCONJ", "PART", "ADP"]:
                continue
            
            if token.pos_ in ["VERB", "AUX", "ADJ", "ADV", "NOUN", "PROPN"]:
                lemma = token.lemma_.lower()
                original_text = token.text
                
                # --- A. 动词修正逻辑 ---
                if source_code == "de" and token.pos_ == "VERB":
                    if lemma.endswith("een") and not lemma.endswith("gehen"):
                        if "et" in original_text.lower(): lemma = lemma.replace("een", "eten")
                        else: lemma = original_text.lower()
                    
                    if original_text.lower() == "brichst": lemma = "brechen"

                    if token.i in particles_map:
                        prefix = particles_map[token.i]
                        if not lemma.startswith(prefix): lemma = prefix + lemma
                
                # --- B. 形容词过滤逻辑 (关键改进) ---
                if token.pos_ == "ADJ":
                    # 如果原形在物主代词排除列表中，直接跳过
                    if lemma in EXCLUDE_PRONOMINAL_ADJS:
                        continue

                # 缓存与展示
                cache_key = f"{lemma}_{token.pos_}"
                if cache_key not in processed_keys:
                    zh_trans = smart_translate(lemma, token.pos_, source_code)
                    aux_trans = GoogleTranslator(source=source_code, target=target_aux_code).translate(lemma)
                    
                    row = {"词原形": lemma, "中文意思": zh_trans, "辅助解析": aux_trans}
                    
                    if token.pos_ in ["VERB", "AUX"]:
                        verb_data.append({"经文动词": original_text, **row})
                    elif token.pos_ in ["NOUN", "PROPN"]:
                        noun_data.append({"经文名词": original_text, **row})
                    else:
                        adj_adv_data.append({"经文原词": original_text, "词类": "形/副", **row})
                    
                    processed_keys.add(cache_key)

        # --- C. 固定搭配提取 ---
        processed_phrases = set()
        for token in doc:
            if token.pos_ == "VERB":
                for child in token.children:
                    if child.dep_ in ["prep", "obl"]:
                        prep = child.text.lower()
                        if child.pos_ == "ADP":
                            idiom = f"{prep} etwas {token.lemma_}"
                            idiom = idiom.replace("übertreen", "übertreten")
                            if idiom not in processed_phrases:
                                zh_idiom = smart_translate(idiom, "PHRASE", source_code)
                                phrase_data.append({"固定搭配": idiom, "中文意思": zh_idiom})
                                processed_phrases.add(idiom)

        # --- 展示表格 ---
        if phrase_data:
            st.subheader("🚀 固定搭配解析")
            st.table(phrase_data)
        
        t1, t2, t3 = st.tabs(["动词解析", "名词解析", "形容词/副词"])
        with t1: st.table(verb_data)
        with t2: st.table(noun_data)
        with t3: st.table(adj_adv_data)

        app.save_dict()
