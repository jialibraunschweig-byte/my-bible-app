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

# --- 2. 核心翻译逻辑：增加清洗功能 ---
def smart_translate(text, pos, source_lang="de"):
    try:
        if source_lang == "de":
            if pos == "VERB":
                # 后台引导语境，确保准确
                query = f"Bedeutung vom Verb '{text}' im Sinne von Gesetz oder Handlung"
            elif pos == "PHRASE":
                query = f"Was bedeutet die Redewendung '{text}'?"
            else:
                query = text
            
            raw_res = GoogleTranslator(source='de', target='zh-CN').translate(query)
            
            # --- 清洗逻辑：去掉冗余说明 ---
            # 过滤掉“动词”、“法律”、“含义”等字眼，只取翻译出的第一个动词或词组
            cleaned_res = raw_res.replace("的意思是", "").replace("含义是", "").replace("在法律或行动意义上的含义", "")
            cleaned_res = cleaned_res.replace("动词", "").replace("指", "").replace("意为", "")
            
            # 如果翻译结果包含引号，提取引号内容；如果包含冒号，取冒号后的内容
            if "“" in cleaned_res and "”" in cleaned_res:
                cleaned_res = cleaned_res.split("“")[1].split("”")[0]
            elif ":" in cleaned_res:
                cleaned_res = cleaned_res.split(":")[-1]
            elif "：" in cleaned_res:
                cleaned_res = cleaned_res.split("：")[-1]
                
            return cleaned_res.strip()
        else:
            return GoogleTranslator(source=source_code, target='zh-CN').translate(text)
    except:
        return "翻译超时"

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
st.info("💡 已修正：动词解析现在将直接显示核心词义，不再显示冗余的语境说明。")

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
    with st.spinner('正在精简解析词条...'):
        nlp = get_nlp(source_code)
        doc = nlp(sentence)
        
        full_zh = GoogleTranslator(source=source_code, target='zh-CN').translate(sentence)
        st.success(f"**全句意译：** {full_zh}")

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
                original_text = token.text.lower()
                
                if (lemma in EXCLUDE_WORDS or original_text in EXCLUDE_WORDS) and token.pos_ == "ADJ":
                    continue

                if source_code == "de" and token.pos_ == "VERB":
                    if lemma.endswith("een") and not lemma.endswith("gehen"):
                        if "et" in original_text: lemma = lemma.replace("een", "eten")
                        else: lemma = original_text
                    if original_text == "brichst": lemma = "brechen"
                    if token.i in particles_map:
                        prefix = particles_map[token.i]
                        if not lemma.startswith(prefix): lemma = prefix + lemma

                cache_key = f"{lemma}_{token.pos_}"
                if cache_key not in processed_keys:
                    zh_trans = smart_translate(lemma, token.pos_, source_code)
                    aux_trans = GoogleTranslator(source=source_code, target=target_aux_code).translate(lemma)
                    
                    row = {"词原形": lemma, "中文意思": zh_trans, "辅助解析": aux_trans}
                    
                    if token.pos_ in ["VERB", "AUX"]:
                        verb_data.append({"经文动词": token.text, **row})
                    elif token.pos_ in ["NOUN", "PROPN"]:
                        noun_data.append({"经文名词": token.text, **row})
                    else:
                        adj_adv_data.append({"经文原词": token.text, "词类": "形/副词", **row})
                    
                    processed_keys.add(cache_key)

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
