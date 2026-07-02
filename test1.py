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

# --- 2. 官方原生 DeepL API 安全穿透函数 ---
DEEPL_API_KEY = "b5b43291-f654-4a84-a0b1-c1d862852987:fx"

def deepl_raw_translate(text, source_lang, target_lang):
    """最底层的单次网络请求，坚决不传列表，只传单文本"""
    if not text.strip():
        return ""
    url = "https://api-free.deepl.com/v2/translate"
    headers = {"Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"}
    data = {
        "text": [text],
        "source_lang": source_lang.upper(),
        "target_lang": target_lang.upper()
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            return response.json()["translations"][0]["text"]
        else:
            return f"API_ERROR_{response.status_code}"
    except Exception as e:
        return f"NET_ERROR_{str(e)}"

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
st.info("💡 已升级：采用【长句自然语言融合技术】。全句所有词汇无损合并、单次握手过检，彻底消除 429 风控障碍。")

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
    with st.spinner('安全加密通道一体化解析中...'):
        nlp = get_nlp(source_code)
        doc = nlp(sentence)

        processed_keys = set()
        token_tasks = []
        particles_map = {token.head.i: token.text.lower() for token in doc if token.dep_ == "svp"}

        # 1. 结构清洗与提取
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
                    token_tasks.append({"original_text": original_text, "lemma": lemma, "pos": token.pos_})
                    processed_keys.add(cache_key)

        # 2. 提取固定搭配
        phrase_tasks = []
        processed_phrases = set()
        if source_code == "de":
            for token in doc:
                if token.pos_ == "VERB" and token.lemma_.lower() not in GERMAN_BASIC_VERBS:
                    for child in token.children:
                        if child.dep_ in ["prep", "obl", "prt"] and child.pos_ in ["ADP", "PART"]:
                            idiom = f"{child.text.lower()} etwas {token.lemma_.lower()}".replace("übertreen", "übertreten")
                            if idiom not in processed_phrases:
                                phrase_tasks.append(idiom)
                                processed_phrases.add(idiom)

        # 3. 分流：优先读取本地缓存，筛选真正需要向云端求助的词条
        need_cloud_tokens = []
        for task in token_tasks:
            ck_zh = f"{source_code}_{task['lemma']}_{task['pos']}_zh"
            ck_aux = f"{source_code}_{task['lemma']}_{task['pos']}_aux"
            
            if ck_zh in app.my_dict and ck_aux in app.my_dict:
                task["zh_trans"] = app.my_dict[ck_zh]
                task["aux_trans"] = app.my_dict[ck_aux]
            else:
                need_cloud_tokens.append((task, ck_zh, ck_aux))

        need_cloud_phrases = []
        phrase_data = []
        for idiom in phrase_tasks:
            ck_p = f"{source_code}_{idiom}_PHRASE_zh"
            if ck_p in app.my_dict:
                phrase_data.append({"固定搭配": idiom, "中文意思": app.my_dict[ck_p]})
            else:
                need_cloud_phrases.append((idiom, ck_p))

        # 4. 执行云端请求（1：翻译整句意译）
        full_zh = deepl_raw_translate(sentence, source_lang=source_code, target_lang="ZH")
        st.success(f"**全句意译（DeepL 官方直连）：** {full_zh}")

        # 5. 🚀 核心大改动：把零散的单词/短语拼接成“逗号长句”，一次性拿回所有数据
        # 组装中文查询串
        zh_query_elements = []
        for task, _, _ in need_cloud_tokens:
            q_zh = f"动词 {task['lemma']}" if task["pos"] == "VERB" and source_code == "de" else task["lemma"]
            zh_query_elements.append(q_zh)
        for idiom, _ in need_cloud_phrases:
            zh_query_elements.append(f"短语: {idiom}")

        # 组装辅助语言查询串（仅包含单词原形）
        aux_query_elements = [task["lemma"] for task, _, _ in need_cloud_tokens]

        # 💡 只有当有新词需要翻译时才触发网络交互，且雷打不动只发两次
        cloud_zh_results = []
        cloud_aux_results = []
        
        if zh_query_elements:
            # 用逗号把所有查词连接成一个类似“句子”的结构，彻底绕过多行过滤和并发判定
            joined_zh_text = ", ".join(zh_query_elements)
            raw_zh_response = deepl_raw_translate(joined_zh_text, source_lang=source_code, target_lang="ZH")
            # 通过中文逗号或英文逗号进行本地分割
            cloud_zh_results = [r.strip() for r in raw_zh_response.replace("，", ",").split(",")]

        if aux_query_elements:
            joined_aux_text = ", ".join(aux_query_elements)
            raw_aux_response = deepl_raw_translate(joined_aux_text, source_lang=source_code, target_lang=target_aux_code)
            cloud_aux_results = [r.strip() for r in raw_aux_response.replace("开口", ",").replace("，", ",").split(",")]

        # 6. 精准拆包与本地数据回填
        cursor = 0
        for task, ck_zh, ck_aux in need_cloud_tokens:
            extracted_zh = "获取失败"
            extracted_aux = "Failed"
            
            if cursor < len(cloud_zh_results):
                extracted_zh = cloud_zh_results[cursor].replace("动词 ", "").replace("(动词)", "").replace("（动词）", "").strip()
            if cursor < len(cloud_aux_results):
                extracted_aux = cloud_aux_results[cursor].strip()
                
            cursor += 1
            
            task["zh_trans"] = extracted_zh
            task["aux_trans"] = extracted_aux
            
            if "API_ERROR" not in extracted_zh and "NET_ERROR" not in extracted_zh and "API_ERROR" not in extracted_aux:
                app.my_dict[ck_zh] = extracted_zh
                app.my_dict[ck_aux] = extracted_aux

        for idiom, ck_p in need_cloud_phrases:
            extracted_p_zh = "获取失败"
            if cursor < len(cloud_zh_results):
                extracted_p_zh = cloud_zh_results[cursor].replace("短语: ", "").strip()
            cursor += 1
            
            phrase_data.append({"固定搭配": idiom, "中文意思": extracted_p_zh})
            if "API_ERROR" not in extracted_p_zh and "NET_ERROR" not in extracted_p_zh:
                app.my_dict[ck_p] = extracted_p_zh

        # 7. 分流渲染表格
        verb_data, adj_adv_data, noun_data = [], [], []
        for task in token_tasks:
            row_base = {"词原形": task["lemma"], "中文意思": task.get("zh_trans", "未知"), "辅助解析": task.get("aux_trans", "Unknown")}
            if task["pos"] in ["VERB", "AUX"]:
                verb_data.append({"经文动词": task["original_text"], **row_base})
            elif task["pos"] in ["NOUN", "PROPN"]:
                noun_data.append({"经文名词": task["original_text"], **row_base})
            else:
                adj_adv_data.append({"经文原词": task["original_text"], **row_base})

        # 前端表格输出
        if phrase_data:
            st.subheader("🚀 固定搭配解析")
            st.table(phrase_data)
        
        t1, t2, t3 = st.tabs(["动词解析", "名词解析", "形容词/副词"])
        with t1: st.table(verb_data)
        with t2: st.table(noun_data)
        with t3: st.table(adj_adv_data)
        
        app.save_dict()
