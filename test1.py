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

# --- 2. 官方原生 DeepL API 门面函数 ---
DEEPL_API_KEY = "b5b43291-f654-4a84-a0b1-c1d862852987:fx"

def deepl_direct_translate(text, source_lang, target_lang):
    """直接通过 HTTP 请求调用 DeepL 官方 API 服务"""
    url = "https://api-free.deepl.com/v2/translate"
    headers = {
        "Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"
    }
    data = {
        "text": [text],
        "source_lang": source_lang.upper(),
        "target_lang": target_lang.upper()
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            return result["translations"][0]["text"]
        else:
            return f"API 状态错误: {response.status_code}"
    except Exception as e:
        return f"网络连接失败: {str(e)}"

def smart_translate(text, pos, source_lang="de"):
    src = source_lang.lower()
    
    # 根据语言动态添加底层提示词提示 DeepL，防止返回带有“简体中文”等杂质
    if pos == "VERB":
        query = f"{text} (Verb)" if src == "de" else f"to {text} (Verb)"
    elif pos == "PHRASE":
        query = f"Redewendung: {text}" if src == "de" else f"Idiom/Phrase: {text}"
    else:
        query = text
    
    translated = deepl_direct_translate(query, source_lang=src, target_lang="ZH")
    
    # 清洗可能残留的标签，保持纯净词义
    cleaned = translated.replace("(动词)", "").replace("动词：", "").replace("短语：", "").replace("习语：", "")
    return cleaned.strip()

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
st.info("💡 已升级：全网重构了固定搭配提取逻辑，完美适配英语/德语双语种，彻底解决翻译夹杂噪音和未翻译问题。")

lang_option = st.radio("选择语言:", ("德语 (Deutsch)", "英语 (English)"), horizontal=True)
source_code = "de" if "德语" in lang_option else "en"

# 官方标准：目标辅助语言代码
target_aux_code = "EN" if source_code == "de" else "DE"

sentence = st.text_area("请粘贴经文内容:", key="input_sentence", height=150)

col1, col2 = st.columns([1, 5])
with col1:
    parse_btn = st.button("开始深度解析")
with col2:
    st.button("清除内容", on_click=clear_text)

if parse_btn and sentence:
    with st.spinner('正在直连 DeepL 官方云端解析...'):
        nlp = get_nlp(source_code)
        doc = nlp(sentence)
        
        # 全句意译
        full_zh = deepl_direct_translate(sentence, source_lang=source_code, target_lang="ZH")
        st.success(f"**全句意译（DeepL 官方直连）：** {full_zh}")

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

                # 词形修正（仅在德语时生效）
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
                    aux_trans = deepl_direct_translate(lemma, source_lang=source_code, target_lang=target_aux_code)
                    
                    row_base = {"词原形": lemma, "中文意思": zh_trans, "辅助解析": aux_trans}
                    
                    if token.pos_ in ["VERB", "AUX"]:
                        verb_data.append({"经文动词": original_text, **row_base})
                    elif token.pos_ in ["NOUN", "PROPN"]:
                        noun_data.append({"经文名词": original_text, **row_base})
                    else:
                        adj_adv_data.append({"经文原词": original_text, **row_base})
                    
                    processed_keys.add(cache_key)

        # --- 🚀 修复核心：多语言固定搭配提取 ---
        processed_phrases = set()
        for token in doc:
            if token.pos_ == "VERB":
                for child in token.children:
                    if child.dep_ in ["prep", "obl", "prt"] and child.pos_ in ["ADP", "PART"]:
                        # 德语动词搭配习惯：介词 + etwas + 动词原形 (如: in etwas verbergen)
                        if source_code == "de":
                            idiom = f"{child.text.lower()} etwas {token.lemma_.lower()}"
                            idiom = idiom.replace("übertreen", "übertreten")
                        # 英语动词搭配习惯：动词原形 + 介词/小品词 (如: hide in / bring to)
                        else:
                            idiom = f"{token.lemma_.lower()} {child.text.lower()}"
                            
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
