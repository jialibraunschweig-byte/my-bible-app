import streamlit as st
import json
import os
import spacy
from deep_translator import DeeplTranslator

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

# --- 2. 核心翻译逻辑：使用 deep-translator 官方标准全称文本 ---
DEEPL_API_KEY = "b5b43291-f654-4a84-a0b1-c1d862852987:fx"

def smart_translate(text, pos, source_lang="de"):
    try:
        # 终极修复：映射为 deep-translator 库内部字典要求的语言英文全称
        src = "german" if source_lang.lower() == "de" else "english"
        tgt = "chinese (simplified)"
        
        translator = DeeplTranslator(api_key=DEEPL_API_KEY, source=src, target=tgt, use_free_api=True)
        
        if src == "german":
            if pos == "VERB":
                query = f"{text} (Verb)"
            elif pos == "PHRASE":
                query = f"Redewendung: {text}"
            else:
                query = text
            
            translated = translator.translate(query)
            return translated.replace("(动词)", "").replace("动词：", "").replace("短语：", "").strip()
        else:
            return translator.translate(text)
    except Exception as e:
        return f"翻译出错了: {str(e)}"

def clear_text():
    st.session_state["input_sentence"] = ""

# --- 3. 增强版排除列表 ---
EXCLUDE_WORDS = {
    "mein", "meine", "meines", "meiner", "meinem", "meinen",
    "dein", "deine", "deines", "deiner", "deinem", "deinen",
    "sein", "seine", "seines", "seiner", "seinem", "seinen",
    "unser", "unsere", "unseres", "unserer", "unserem", "unseren",
    "euer", "eure", "eures", "eurer", "eurem", "euren",
    "ihr", "ihre", "ihres", "ihrer", "ihrem", "ihren",
    "dieser", "dieses", "diese", "diesem", "diesen", "dieser",
    "jener", "solcher", "welcher"
}

st.title("📖 德语经文精准解析器")
st.info("💡 已修正：改用官方推荐的英文全称语言映射模式（"chinese (simplified)"），跳过不稳定的简写映射。")

lang_option = st.radio("选择语言:", ("德语 (Deutsch)", "英语 (English)"), horizontal=True)
source_code = "de" if "德语" in lang_option else "en"

# 终极修复：辅助解析目标语言全称
target_aux_code = "english" if source_code == "de" else "german"

sentence = st.text_area("请粘贴德语内容:", key="input_sentence", height=150)

col1, col2 = st.columns([1, 5])
with col1:
    parse_btn = st.button("开始深度解析")
with col2:
    st.button("清除内容", on_click=clear_text)

GERMAN_PREFIXES = {"ab", "an", "auf", "aus", "bei", "ein", "empor", "entgegen", "fest", "fort", "her", "hin", "los", "nach", "nieder", "vor", "weg", "weiter", "zu", "zurück", "zusammen", "um"}

if parse_btn and sentence:
    with st.spinner('DeepL 引擎正在深度解析词条...'):
        nlp = get_nlp(source_code)
        doc = nlp(sentence)
        
        # 终极修复：全句意译转换
        src_full = "german" if source_code == "de" else "english"
        full_translator = DeeplTranslator(api_key=DEEPL_API_KEY, source=src_full, target="chinese (simplified)", use_free_api=True)
        full_zh = full_translator.translate(sentence)
        st.success(f"**全句意译（DeepL 驱动）：** {full_zh}")

        verb_data, adj_adv_data, noun_data, phrase_data = [], [], [], []
        processed_keys = set()

        particles_map = {}
        for token in doc:
            if token.dep_ == "svp":
                particles_map[token.head.i] = token.text.lower()

        for token in doc:
            if token.is_punct or token.is_space or token.pos_ in ["PRON", "DET", "CONJ", "SCONJ", "PART", "ADP"]:
                continue
            
            if token.pos_ in ["VERB", "AUX", "ADJ", "ADV", "NOUN", "PROPN"]:
                lemma = token.lemma_.lower()
                original_text = token.text
                
                # 过滤代词形容词
                if (lemma in EXCLUDE_WORDS or original_text.lower() in EXCLUDE_WORDS) and token.pos_ == "ADJ":
                    continue

                # 词形修正
                if source_code == "de" and token.pos_ == "VERB":
                    if lemma.endswith("een") and not lemma.endswith("gehen"):
                        if "et" in original_text.lower(): lemma = lemma.replace("een", "eten")
                        else: lemma = original_text.lower()
                    if original_text.lower() == "brichst": lemma = "brechen"
                    if token.i in particles_map:
                        prefix = particles_map[token.i]
                        if not lemma.startswith(prefix): lemma = prefix + lemma

                cache_key = f"{lemma}_{token.pos_}"
                if cache_key not in processed_keys:
                    zh_trans = smart_translate(lemma, token.pos_, source_code)
                    
                    # 终极修复：辅助解析使用全称
                    aux_translator = DeeplTranslator(api_key=DEEPL_API_KEY, source=src_full, target=target_aux_code, use_free_api=True)
                    aux_trans = aux_translator.translate(lemma)
                    
                    # 公共行数据
                    row_base = {"词原形": lemma, "中文意思": zh_trans, "辅助解析": aux_trans}
                    
                    if token.pos_ in ["VERB", "AUX"]:
                        verb_data.append({"经文动词": original_text, **row_base})
                    elif token.pos_ in ["NOUN", "PROPN"]:
                        noun_data.append({"经文名词": original_text, **row_base})
                    else:
                        adj_adv_data.append({"经文原词": original_text, **row_base})
                    
                    processed_keys.add(cache_key)

        # 固定搭配
        processed_phrases = set()
        for token in doc:
            if token.pos_ == "VERB":
                for child in token.children:
                    if child.dep_ in ["prep", "obl"] and child.pos_ == "ADP":
                        idiom = f"{child.text.lower()} etwas {token.lemma_.lower()}"
                        idiom = idiom.replace("übertreen", "übertreten")
                        if idiom not in processed_phrases:
                            zh_idiom = smart_translate(idiom, "PHRASE", source_code)
                            phrase_data.append({"固定搭配": idiom, "中文意思": zh_idiom})
                            processed_phrases.add(idiom)

        if phrase_data:
            st.subheader("🚀 固定搭配解析")
            st.table(phrase_data)
        
        t1, t2, t3 = st.tabs(["动词解析", "名词解析", "形容词/副词"])
        with t1: st.table(verb_data)
        with t2: st.table(noun_data)
        with t3: st.table(adj_adv_data)
        
        app.save_dict()
