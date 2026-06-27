import streamlit as st
import json
import os
import spacy
import requests
import time  # 🚀 引入时间模块，用于精准限速隔离

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

# --- 2. 官方原生 DeepL API 稳定防御函数 ---
DEEPL_API_KEY = "b5b43291-f654-4a84-a0b1-c1d862852987:fx"

def deepl_direct_translate(text, source_lang, target_lang):
    """直接通过安全请求调用 DeepL 官方 API，内置指数级退避重试防御机制"""
    url = "https://api-free.deepl.com/v2/translate"
    headers = {
        "Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"
    }
    data = {
        "text": [text],
        "source_lang": source_lang.upper(),
        "target_lang": target_lang.upper()
    }
    
    max_retries = 4
    for attempt in range(max_retries):
        try:
            # 🚀 在每次网络请求前，强制加入微观的时间间隔，避免突发高频请求触发429
            time.sleep(0.25)
            response = requests.post(url, headers=headers, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                return result["translations"][0]["text"]
            elif response.status_code == 429:
                # 🚀 若仍遇到流控，成倍延长等待时间再试
                time.sleep(2.0 * (attempt + 1))
                continue
            else:
                return f"API 状态错误: {response.status_code}"
        except Exception as e:
            if attempt == max_retries - 1:
                return f"网络连接失败: {str(e)}"
            time.sleep(1.0)
            
    return "API 错误: 线路过于繁忙 (429)"

def smart_translate(text, pos, source_lang="de"):
    src = source_lang.lower()
    
    if pos == "VERB":
        query = f"{text} (Verb)" if src == "de" else f"to {text} (Verb)"
    elif pos == "PHRASE":
        query = f"Redewendung: {text}" if src == "de" else f"Idiom/Phrase: {text}"
    else:
        query = text
    
    translated = deepl_direct_translate(query, source_lang=src, target_lang="ZH")
    
    # 移除多余标签
    cleaned = translated.replace("(动词)", "").replace("（动词）", "").replace("动词：", "").replace("短语：", "").replace("习语：", "")
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

# 德语高频基础动词过滤库
GERMAN_BASIC_VERBS = {
    "sein", "ist", "sind", "war", "gewesen",
    "haben", "hat", "hatte", "gehabt",
    "werden", "wird", "wurde", "geworden", "werdet",
    "müssen", "muss", "musste", "gemusst",
    "können", "kann", "konnte", "gekonnt",
    "wollen", "will", "wollte", "gewollt",
    "sollen", "soll", "sollte", "gesollt",
    "kommen", "kommt", "kam", "gekommen",
    "gehen", "geht", "ging", "gegangen"
}

# 英语高频基础动词过滤库
ENGLISH_BASIC_VERBS = {
    "be", "is", "am", "are", "was", "were", "been", "being", "'s", "'re", "wasn't", "weren't", "isn't", "aren't",
    "have", "has", "had", "having", "'ve", "'d", "hasn't", "haven't", "hadn't",
    "do", "does", "did", "done", "doing", "doesn't", "don't", "didn't",
    "come", "comes", "came", "coming",
    "go", "goes", "went", "gone", "going",
    "will", "would", "shall", "should", "can", "could", "may", "might", "must", "ought",
    "won't", "wouldn't", "shouldn't", "can't", "couldn't", "mustn't"
}

st.title("📖 德语经文精准解析器")
st.info("💡 已升级：改用【微秒级安全物理阻断】+【本地数据隔离回填】，彻底攻克 429 报错难题。")

lang_option = st.radio("选择语言:", ("德语 (Deutsch)", "英语 (English)"), horizontal=True)
source_code = "de" if "德语" in lang_option else "en"
target_aux_code = "EN" if source_code == "de" else "DE"

sentence = st.text_area("请粘贴经文内容:", key="input_sentence", height=150)

col1, col2 = st.columns([1, 5])
with col1:
    parse_btn = st.button("开始深度解析")
with col2:
    st.button("清除内容", on_click=clear_text)

if parse_btn and sentence:
    with st.spinner('正在通过 DeepL 官方抗流控通道逐层稳健解析中...'):
        nlp = get_nlp(source_code)
        doc = nlp(sentence)
        
        # 全句意译
        full_zh = deepl_direct_translate(sentence, source_lang=source_code, target_lang="ZH")
        st.success(f"**全句意译（DeepL 官方直连）：** {full_zh}")

        verb_data, adj_adv_data, noun_data, phrase_data = [], [], [], []
        processed_keys = set()
        tasks = []

        particles_map = {token.head.i: token.text.lower() for token in doc if token.dep_ == "svp"}

        # 1. 结构化过滤与词条提取
        for token in doc:
            if token.is_punct or token.is_space or token.pos_ in ["PRON", "DET", "CONJ", "SCONJ", "PART", "ADP"]:
                continue
            
            if token.pos_ in ["VERB", "AUX", "ADJ", "ADV", "NOUN", "PROPN"]:
                lemma = token.lemma_.lower()
                original_text = token.text
                
                if source_code == "de" and (lemma in GERMAN_BASIC_VERBS or original_text.lower() in GERMAN_BASIC_VERBS):
                    continue
                elif source_code == "en" and (lemma in ENGLISH_BASIC_VERBS or original_text.lower() in ENGLISH_BASIC_VERBS):
                    continue
                
                if (lemma in EXCLUDE_WORDS or original_text.lower() in EXCLUDE_WORDS) and token.pos_ == "ADJ":
                    continue

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
                    tasks.append({"original_text": original_text, "lemma": lemma, "pos": token.pos_})
                    processed_keys.add(cache_key)

        # 2. 串行安全调取（优先查缓存，若无缓存则带有微等待地请求 DeepL）
        for task in tasks:
            cache_key_zh = f"{source_code}_{task['lemma']}_{task['pos']}_zh"
            cache_key_aux = f"{source_code}_{task['lemma']}_{task['pos']}_aux"
            
            if cache_key_zh in app.my_dict and cache_key_aux in app.my_dict:
                zh_trans = app.my_dict[cache_key_zh]
                aux_trans = app.my_dict[cache_key_aux]
            else:
                zh_trans = smart_translate(task['lemma'], task['pos'], source_code)
                aux_trans = deepl_direct_translate(task['lemma'], source_lang=source_code, target_lang=target_aux_code)
                
                if "API" not in zh_trans and "API" not in aux_trans:
                    app.my_dict[cache_key_zh] = zh_trans
                    app.my_dict[cache_key_aux] = aux_trans

            row_base = {"词原形": task["lemma"], "中文意思": zh_trans, "辅助解析": aux_trans}
            if task["pos"] in ["VERB", "AUX"]:
                verb_data.append({"经文动词": task["original_text"], **row_base})
            elif task["pos"] in ["NOUN", "PROPN"]:
                noun_data.append({"经文名词": task["original_text"], **row_base})
            else:
                adj_adv_data.append({"经文原词": task["original_text"], **row_base})

        # 3. 提取并分析固定搭配
        processed_phrases = set()
        for token in doc:
            if source_code == "en":
                continue

            if token.pos_ == "VERB" and token.lemma_.lower() not in GERMAN_BASIC_VERBS:
                for child in token.children:
                    if child.dep_ in ["prep", "obl", "prt"] and child.pos_ in ["ADP", "PART"]:
                        idiom = f"{child.text.lower()} etwas {token.lemma_.lower()}".replace("übertreen", "übertreten")
                            
                        if idiom not in processed_phrases:
                            cache_key_p = f"{source_code}_{idiom}_PHRASE_zh"
                            if cache_key_p in app.my_dict:
                                zh_idiom = app.my_dict[cache_key_p]
                            else:
                                zh_idiom = smart_translate(idiom, "PHRASE", source_code)
                                if "API" not in zh_idiom:
                                    app.my_dict[cache_key_p] = zh_idiom
                            
                            phrase_data.append({"固定搭配": idiom, "中文意思": zh_idiom})
                            processed_phrases.add(idiom)

        # 4. 渲染前端表格
        if phrase_data:
            st.subheader("🚀 固定搭配解析")
            st.table(phrase_data)
        
        t1, t2, t3 = st.tabs(["动词解析", "名词解析", "形容词/副词"])
        with t1: st.table(verb_data)
        with t2: st.table(noun_data)
        with t3: st.table(adj_adv_data)
        
        app.save_dict()
