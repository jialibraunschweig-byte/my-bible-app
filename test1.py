import streamlit as st
import json
import os
import spacy
import requests

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

# --- 2. 核心定义 ---
DEEPL_API_KEY = "b5b43291-f654-4a84-a0b1-c1d862852987:fx"

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

GERMAN_BASIC_VERBS = {
    "sein", "ist", "sind", "war", "gewesen", "haben", "hat", "hatte", "gehabt",
    "werden", "wird", "wurde", "geworden", "müssen", "muss", "musste", "gemusst",
    "können", "kann", "konnte", "gekonnt", "wollen", "will", "wollte", "gewollt",
    "sollen", "soll", "sollte", "gesollt", "kommen", "kommt", "kam", "gekommen",
    "gehen", "geht", "ging", "gegangen"
}

ENGLISH_BASIC_VERBS = {
    "be", "is", "am", "are", "was", "were", "been", "being", "'s", "'re", "wasn't", "weren't", "isn't", "aren't",
    "have", "has", "had", "having", "'ve", "'d", "hasn't", "haven't", "hadn't",
    "do", "does", "did", "done", "doing", "doesn't", "don't", "didn't",
    "come", "comes", "came", "coming", "go", "goes", "went", "gone", "going",
    "will", "would", "shall", "should", "can", "could", "may", "might", "must", "ought",
    "won't", "wouldn't", "shouldn't", "can't", "couldn't", "mustn't"
}

def is_basic_word(lemma, text, pos, source_code):
    """检测是否为基本词汇的辅助函数"""
    if pos in ["VERB", "AUX"]:
        if source_code == "de":
            return lemma in GERMAN_BASIC_VERBS or text.lower() in GERMAN_BASIC_VERBS
        if source_code == "en":
            return lemma in ENGLISH_BASIC_VERBS or text.lower() in ENGLISH_BASIC_VERBS
    return False

def deepl_direct_translate(text, source_lang, target_lang):
    url = "https://api-free.deepl.com/v2/translate"
    headers = {"Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"}
    data = {"text": [text], "source_lang": source_lang.upper(), "target_lang": target_lang.upper()}
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        return response.json()["translations"][0]["text"] if response.status_code == 200 else f"API 状态错误: {response.status_code}"
    except Exception as e:
        return f"网络连接失败: {str(e)}"

def smart_translate(text, pos, source_lang="de"):
    src = source_lang.lower()
    query = f"{text} (Verb)" if pos == "VERB" else (f"Idiom/Phrase: {text}" if pos == "PHRASE" else text)
    translated = deepl_direct_translate(query, source_lang=src, target_lang="ZH")
    return translated.replace("(动词)", "").replace("（动词）", "").replace("动词：", "").replace("短语：", "").replace("习语：", "").strip()

def clear_text(): st.session_state["input_sentence"] = ""

# --- 3. 页面与处理逻辑 ---
st.title("📖 德语经文精准解析器")
lang_option = st.radio("选择语言:", ("德语 (Deutsch)", "英语 (English)"), horizontal=True)
source_code = "de" if "德语" in lang_option else "en"
target_aux_code = "EN" if source_code == "de" else "DE"

sentence = st.text_area("请粘贴经文内容:", key="input_sentence", height=150)

if st.button("开始深度解析") and sentence:
    nlp = get_nlp(source_code)
    doc = nlp(sentence)
    full_zh = deepl_direct_translate(sentence, source_lang=source_code, target_lang="ZH")
    st.success(f"**全句意译：** {full_zh}")

    verb_data, adj_adv_data, noun_data, phrase_data = [], [], [], []
    processed_keys = set()
    particles_map = {token.head.i: token.text.lower() for token in doc if token.dep_ == "svp"}

    for token in doc:
        if token.is_punct or token.is_space or token.pos_ in ["PRON", "DET", "CONJ", "SCONJ", "PART", "ADP"]:
            continue
        
        if token.pos_ in ["VERB", "AUX", "ADJ", "ADV", "NOUN", "PROPN"]:
            lemma, original_text = token.lemma_.lower(), token.text
            
            # 初次拦截
            if is_basic_word(lemma, original_text, token.pos_, source_code):
                continue
                
            if (lemma in EXCLUDE_WORDS or original_text.lower() in EXCLUDE_WORDS) and token.pos_ == "ADJ":
                continue

            if source_code == "de" and token.pos_ == "VERB":
                if lemma.endswith("een") and not lemma.endswith("gehen"):
                    lemma = lemma.replace("een", "eten") if "et" in original_text.lower() else original_text.lower()
                if original_text.lower() == "brichst": lemma = "brechen"
                if token.i in particles_map and not lemma.startswith(particles_map[token.i]):
                    lemma = particles_map[token.i] + lemma

            cache_key = f"{lemma}_{token.pos_}"
            # 二次拦截：确保处理后的词也不是基本词
            if cache_key not in processed_keys and not is_basic_word(lemma, lemma, token.pos_, source_code):
                zh_trans = smart_translate(lemma, token.pos_, source_code)
                aux_trans = deepl_direct_translate(lemma, source_lang=source_code, target_lang=target_aux_code)
                row = {"词原形": lemma, "中文意思": zh_trans, "辅助解析": aux_trans}
                
                if token.pos_ in ["VERB", "AUX"]: verb_data.append({"经文动词": original_text, **row})
                elif token.pos_ in ["NOUN", "PROPN"]: noun_data.append({"经文名词": original_text, **row})
                else: adj_adv_data.append({"经文原词": original_text, **row})
                processed_keys.add(cache_key)

    # 显示结果
    t1, t2, t3 = st.tabs(["动词解析", "名词解析", "形容词/副词"])
    with t1: st.table(verb_data)
    with t2: st.table(noun_data)
    with t3: st.table(adj_adv_data)
    app.save_dict()
