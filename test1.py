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
            # 过滤拦截各种可能返回的流控脏数据文本，防止其被写入缓存
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

# 🚀 德语强变化/虚拟式特殊动词及脚注特征劫持映射表
SPECIAL_VERB_LEMMA_MAP = {
    "herumliefe": "herumlaufen",
    "liefe": "laufen",
    "brichst": "brechen",
    "unterbricht": "unterbrechen"
}

st.title("📖 德语经文精准解析器")
st.info("💡 已升级：修复可分离虚拟式动词（如 herumliefe 还原为 herumlaufen）识别规则，并增强了防 429 脏数据穿透过滤。")

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
        # 0. 预处理：清洗掉可能附带的经文原始脚注干扰（如 [2], .[3] 等）
        clean_sentence = re.sub(r'\[\d+\]', '', sentence)
        clean_sentence = re.sub(r'\.\[\d+\]', '.', clean_sentence)

        nlp = get_nlp(source_code)
        doc = nlp(clean_sentence)

        processed_keys = set()
        token_tasks = []
        particles_map = {token.head.i: token.text.lower() for token in doc if token.dep_ == "svp"}

        # 1. 结构清洗与提取
        for token in doc:
            # 彻底剥离多余的数字标点干扰
            raw_text_clean = re.sub(r'\d+', '', token.text).strip("[] .")
            if not raw_text_clean or token.is_punct or token.is_space or token.pos_ in ["PRON", "DET", "CONJ", "SCONJ", "PART", "ADP"]:
                continue
            
            if token.pos_ in ["VERB", "AUX", "ADJ", "ADV", "NOUN", "PROPN"]:
                original_text = token.text
                # 清除单词本身夹杂的脚注尾缀
                original_text_clean = re.sub(r'\[\d+\]', '', original_text).strip(". ")
                
                # 🚀 优先触发动词硬核拦截劫持
                lower_raw = original_text_clean.lower()
                if source_code == "de" and lower_raw in SPECIAL_VERB_LEMMA_MAP:
                    lemma = SPECIAL_VERB_LEMMA_MAP[lower_raw]
                    current_pos = "VERB" # 强制修正由于格式错乱被误判的词性
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
            
            if ck_zh in app.my_dict and ck_aux in app.my_dict and "429" not in str(app.my_dict[ck_zh]):
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

        # 5. 安全长串序列化发送（加入格式前缀引导，防止DeepL内部把结果错位）
        zh_query_elements = []
        for task, _, _ in need_cloud_tokens:
            q_zh = f"动词 {task['lemma']}" if task["pos"] == "VERB" and source_code == "de" else task["lemma"]
            zh_query_elements.append(q_zh)
        for idiom, _ in need_cloud_phrases:
            zh_query_elements.append(f"短语: {idiom}")

        aux_query_elements = [task["lemma"] for task, _, _ in need_cloud_tokens]

        cloud_zh_results = []
        cloud_aux_results = []
        
        if zh_query_elements:
            joined_zh_text = "Words: " + ", ".join(zh_query_elements)
            raw_zh_response = deepl_raw_translate(joined_zh_text, source_lang=source_code, target_lang="ZH")
            raw_zh_clean = raw_zh_response.replace("Words:", "").replace("单词:", "").replace("词语:", "")
            cloud_zh_results = [r.strip() for r in raw_zh_clean.replace("，", ",").split(",")]

        if aux_query_elements:
            joined_aux_text = "Words: " + ", ".join(aux_query_elements)
            raw_aux_response = deepl_raw_translate(joined_aux_text, source_lang=source_code, target_lang=target_aux_code)
            raw_aux_clean = raw_aux_response.replace("Words:", "").replace("单词:", "")
            cloud_aux_results = [r.strip() for r in raw_aux_clean.replace("，", ",").split(",")]

        # 6. 数据回归拆包回填与防抖核验
        cursor = 0
        for task, ck_zh, ck_aux in need_cloud_tokens:
            extracted_zh = "暂无译文"
            extracted_aux = "Failed"
            
            if cursor < len(cloud_zh_results) and cloud_zh_results[cursor]:
                res_v = cloud_zh_results[cursor].replace("动词 ", "").replace("(动词)", "").replace("（动词）", "").strip()
                if "429" not in res_v and "错误" not in res_v: extracted_zh = res_v
            if cursor < len(cloud_aux_results) and cloud_aux_results[cursor]:
                res_a = cloud_aux_results[cursor].strip()
                if "429" not in res_a and "错误" not in res_a: extracted_aux = res_a
                
            cursor += 1
            task["zh_trans"] = extracted_zh
            task["aux_trans"] = extracted_aux
            
            if extracted_zh != "暂无译文" and extracted_aux != "Failed":
                app.my_dict[ck_zh] = extracted_zh
                app.my_dict[ck_aux] = extracted_aux

        for idiom, ck_p in need_cloud_phrases:
            extracted_p_zh = "暂无译文"
            if cursor < len(cloud_zh_results) and cloud_zh_results[cursor]:
                res_p = cloud_zh_results[cursor].replace("短语: ", "").strip()
                if "429" not in res_p: extracted_p_zh = res_p
            cursor += 1
            
            phrase_data.append({"固定搭配": idiom, "中文意思": extracted_p_zh})
            if extracted_p_zh != "暂无译文":
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
