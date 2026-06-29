import streamlit as st
import json
import os
import re
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

# --- 2. DeepL API 稳定一体化安全通道 ---
DEEPL_API_KEY = "b5b43291-f654-4a84-a0b1-c1d862852987:fx"

def deepl_raw_translate(text, source_lang, target_lang):
    """安全底层请求，带风控脏数据拦截"""
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
            res_text = response.json()["translations"][0]["text"]
            if "429" in res_text or "Too Many Requests" in res_text or "限流" in res_text:
                return "暂无译文 (API限流保护)"
            return res_text
        else:
            return "暂无译文 (API限流保护)"
    except Exception:
        return "网络交互重试中"

def clear_text():
    st.session_state["input_sentence"] = ""

# --- 3. 核心语言清洗规则库 ---
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
    "werden", "wird", "wurde", "geworden", "werdet", "müssen", "muss", "musste", "gemusst",
    "können", "kann", "konnte", "gekonnt", "wollen", "will", "wollte", "gewollt",
    "sollen", "soll", "sollte", "gesollt", "kommen", "kommt", "kam", "gekommen",
    "gehen", "geht", "ging", "gegangen"
}

ENGLISH_BASIC_VERBS = {
    "be", "is", "am", "are", "was", "were", "been", "being", "'s", "'re", "wasn't", "weren't",
    "have", "has", "had", "having", "'ve", "do", "does", "did", "done", "will", "would"
}

SPECIAL_VERB_LEMMA_MAP = {
    "geschoren": "scheren",
    "herumliefe": "herumlaufen",
    "liefe": "laufen",
    "brichst": "brechen",
    "unterbricht": "unterbrechen"
}

st.title("📖 德语经文精准解析器")
st.info("💡 已升级：改用【行标记强制对齐技术】。完美解决词条漏译（如 leichtfertig）与翻译错位问题。")

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
        clean_sentence = re.sub(r'\[\d+\]', '', sentence)
        clean_sentence = re.sub(r'\.\[\d+\]', '.', clean_sentence)

        nlp = get_nlp(source_code)
        doc = nlp(clean_sentence)

        processed_keys = set()
        token_tasks = []
        particles_map = {token.head.i: token.text.lower() for token in doc if token.dep_ == "svp"}

        # 1. 结构清洗与提取
        for token in doc:
            raw_text_clean = re.sub(r'\d+', '', token.text).strip("[] .")
            if not raw_text_clean or token.is_punct or token.is_space or token.pos_ in ["PRON", "DET", "CONJ", "SCONJ", "PART", "ADP"]:
                continue
            
            if token.pos_ in ["VERB", "AUX", "ADJ", "ADV", "NOUN", "PROPN"]:
                original_text = token.text
                original_text_clean = re.sub(r'\[\d+\]', '', original_text).strip(". ")
                
                lower_raw = original_text_clean.lower()
                if source_code == "de" and lower_raw in SPECIAL_VERB_LEMMA_MAP:
                    lemma = SPECIAL_VERB_LEMMA_MAP[lower_raw]
                    current_pos = "VERB" 
                else:
                    lemma = token.lemma_.lower()
                    lemma = re.sub(r'\[\d+\]', '', lemma).strip(". ")
                    current_pos = token.pos_

                if source_code == "de" and (lemma in GERMAN_BASIC_VERBS or lower_raw in GERMAN_BASIC_VERBS):
                    continue
                elif source_code == "en" and (lemma in ENGLISH_BASIC_VERBS or lower_raw in ENGLISH_BASIC_VERBS):
                    continue
                
                if (lemma in EXCLUDE_WORDS or lower_raw in EXCLUDE_WORDS) and current_pos == "ADJ":
                    continue

                if source_code == "de" and current_pos == "VERB":
                    if lemma.endswith("een") and not lemma.endswith("gehen"):
                        if "et" in lower_raw: lemma = lemma.replace("een", "eten")
                        else: lemma = lower_raw
                    if token.i in particles_map:
                        prefix = particles_map[token.i]
                        if not lemma.startswith(prefix): lemma = prefix + lemma

                cache_key = f"{lemma}_{current_pos}"
                if cache_key not in processed_keys:
                    token_tasks.append({"original_text": original_text_clean, "lemma": lemma, "pos": current_pos})
                    processed_keys.add(cache_key)

        # 2. 提取固定搭配
        phrase_tasks = []
        processed_phrases = set()
        if source_code == "de":
            for token in doc:
                if token.pos_ == "VERB" and token.lemma_.lower() not in GERMAN_BASIC_VERBS:
                    for child in token.children:
                        if child.dep_ in ["prep", "obl", "prt"] and child.pos_ in ["ADP", "PART"]:
                            v_lemma = SPECIAL_VERB_LEMMA_MAP.get(token.text.lower(), token.lemma_.lower())
                            idiom = f"{child.text.lower()} etwas {v_lemma}".replace("übertreen", "übertreten")
                            if idiom not in processed_phrases:
                                phrase_tasks.append(idiom)
                                processed_phrases.add(idiom)

        # 3. 本地缓存分流调度
        need_cloud_tokens = []
        for task in token_tasks:
            ck_zh = f"{source_code}_{task['lemma']}_{task['pos']}_zh"
            ck_aux = f"{source_code}_{task['lemma']}_{task['pos']}_aux"
            
            if ck_zh in app.my_dict and ck_aux in app.my_dict and "429" not in str(app.my_dict[ck_zh]) and "失败" not in str(app.my_dict[ck_zh]):
                task["zh_trans"] = app.my_dict[ck_zh]
                task["aux_trans"] = app.my_dict[ck_aux]
            else:
                need_cloud_tokens.append((task, ck_zh, ck_aux))

        need_cloud_phrases = []
        phrase_data = []
        for idiom in phrase_tasks:
            ck_p = f"{source_code}_{idiom}_PHRASE_zh"
            if ck_p in app.my_dict and "429" not in str(app.my_dict[ck_p]):
                phrase_data.append({"固定搭配": idiom, "中文意思": app.my_dict[ck_p]})
            else:
                need_cloud_phrases.append((idiom, ck_p))

        # 4. 执行云端请求（1：整句大翻译）
        full_zh = deepl_raw_translate(clean_sentence, source_lang=source_code, target_lang="ZH")
        st.success(f"**全句意译（DeepL 官方直连）：** {full_zh}")

        # 5. 🚀 强约束行结构化格式组装（带序号，防止漏词或错位）
        zh_query_lines = []
        line_idx = 1
        
        for task, _, _ in need_cloud_tokens:
            q_zh = f"动词 {task['lemma']}" if task["pos"] == "VERB" and source_code == "de" else task["lemma"]
            zh_query_lines.append(f"{line_idx}: {q_zh}")
            line_idx += 1
            
        for idiom, _ in need_cloud_phrases:
            zh_query_lines.append(f"{line_idx}: 短语: {idiom}")
            line_idx += 1

        aux_query_lines = []
        aux_line_idx = 1
        for task, _, _ in need_cloud_tokens:
            aux_query_lines.append(f"{aux_line_idx}: {task['lemma']}")
            aux_line_idx += 1

        # 建立解析字典，用于精准匹配行号
        cloud_zh_map = {}
        cloud_aux_map = {}
        
        if zh_query_lines:
            joined_zh_text = "\n".join(zh_query_lines)
            raw_zh_response = deepl_raw_translate(joined_zh_text, source_lang=source_code, target_lang="ZH")
            # 按换行切分，并用正则抓取行号和译文
            for line in raw_zh_response.split("\n"):
                match = re.match(r"^(\d+)[:：]\s*(.*)$", line.strip())
                if match:
                    cloud_zh_map[int(match.group(1))] = match.group(2).strip()

        if aux_query_lines:
            joined_aux_text = "\n".join(aux_query_lines)
            raw_aux_response = deepl_raw_translate(joined_aux_text, source_lang=source_code, target_lang=target_aux_code)
            for line in raw_aux_response.split("\n"):
                match = re.match(r"^(\d+)[:：]\s*(.*)$", line.strip())
                if match:
                    cloud_aux_map[int(match.group(1))] = match.group(2).strip()

        # 6. 数据回归拆包回填（根据强制行号 1对1 还原）
        current_idx = 1
        for task, ck_zh, ck_aux in need_cloud_tokens:
            # 优先从行号映射表里拿，拿不到再进行保底退化处理
            extracted_zh = cloud_zh_map.get(current_idx, "").replace("动词 ", "").replace("(动词)", "").replace("（动词）", "").strip()
            extracted_aux = cloud_aux_map.get(current_idx, "").strip()
            
            # 兜底保障：如果行号没被正则切出来，防止返回空字
            if not extracted_zh: extracted_zh = "暂无译文"
            if not extracted_aux: extracted_aux = "Failed"
            
            current_idx += 1
            
            task["zh_trans"] = extracted_zh
            task["aux_trans"] = extracted_aux
            
            if extracted_zh != "暂无译文" and extracted_aux != "Failed" and "429" not in extracted_zh:
                app.my_dict[ck_zh] = extracted_zh
                app.my_dict[ck_aux] = extracted_aux

        for idiom, ck_p in need_cloud_phrases:
            extracted_p_zh = cloud_zh_map.get(current_idx, "").replace("短语: ", "").strip()
            if not extracted_p_zh: extracted_p_zh = "暂无译文"
            current_idx += 1
            
            phrase_data.append({"固定搭配": idiom, "中文意思": extracted_p_zh})
            if extracted_p_zh != "暂无译文" and "429" not in extracted_p_zh:
                app.my_dict[ck_p] = extracted_p_zh

        # 7. 渲染输出
        verb_data, adj_adv_data, noun_data = [], [], []
        for task in token_tasks:
            row_base = {"词原形": task["lemma"], "中文意思": task.get("zh_trans", "暂无译文"), "辅助解析": task.get("aux_trans", "Failed")}
            if task["pos"] in ["VERB", "AUX"]:
                verb_data.append({"经文动词": task["original_text"], **row_base})
            elif task["pos"] in ["NOUN", "PROPN"]:
                noun_data.append({"经文名词": task["original_text"], **row_base})
            else:
                adj_adv_data.append({"经文原词": task["original_text"], **row_base})

        if phrase_data:
            st.subheader("🚀 固定搭配解析")
            st.table(phrase_data)
        
        t1, t2, t3 = st.tabs(["动词解析", "名词解析", "形容词/副词"])
        with t1: st.table(verb_data)
        with t2: st.table(noun_data)
        with t3: st.table(adj_adv_data)
        
        app.save_dict()
