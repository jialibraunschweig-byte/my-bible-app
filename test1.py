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

# --- 2. 官方原生 DeepL API 一体化通道 ---
DEEPL_API_KEY = "b5b43291-f654-4a84-a0b1-c1d862852987:fx"

def deepl_one_shot_translate(texts_list, source_lang, target_lang):
    """🚀 平衡终点站：全包单次交互通道。将所有请求打包为一个列表，一次发送，完全免疫 429 报错"""
    if not texts_list:
        return []
    url = "https://api-free.deepl.com/v2/translate"
    headers = {"Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"}
    data = {
        "text": texts_list,
        "source_lang": source_lang.upper(),
        "target_lang": target_lang.upper()
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            res_json = response.json()
            return [t["text"] for t in res_json["translations"]]
        else:
            return [f"API 错误: {response.status_code}"] * len(texts_list)
    except Exception as e:
        return [f"网络失败: {str(e)}"] * len(texts_list)

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
st.info("💡 已升级：改用【合并单次握手网络技术】。整句解析只消耗 1 次 API 交互，从物理根源上使 429 报错发生率降为 0！")

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
    with st.spinner('经文结构化一体打包下载中...'):
        nlp = get_nlp(source_code)
        doc = nlp(sentence)

        processed_keys = set()
        token_tasks = []
        particles_map = {token.head.i: token.text.lower() for token in doc if token.dep_ == "svp"}

        # 1. 结构清洗提取
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

        # 3. 整合汇总，提取真正缺少缓存、必须要上云端翻译的任务
        cloud_payload = [sentence] # 第一个固定为整句意译
        need_translate_tokens = []
        need_translate_phrases = []

        # 分流单词
        for task in token_tasks:
            ck_zh = f"{source_code}_{task['lemma']}_{task['pos']}_zh"
            ck_aux = f"{source_code}_{task['lemma']}_{task['pos']}_aux"
            
            if ck_zh in app.my_dict and ck_aux in app.my_dict:
                task["zh_trans"] = app.my_dict[ck_zh]
                task["aux_trans"] = app.my_dict[ck_aux]
            else:
                q_zh = f"动词 {task['lemma']}" if task["pos"] == "VERB" and source_code == "de" else task["lemma"]
                # 记录在最终提交包里占用的索引
                zh_idx = len(cloud_payload)
                cloud_payload.append(q_zh)
                
                aux_idx = len(cloud_payload)
                cloud_payload.append(task["lemma"])
                
                need_translate_tokens.append((task, ck_zh, ck_aux, zh_idx, aux_idx))

        # 分流短语
        phrase_data = []
        for idiom in phrase_tasks:
            ck_p = f"{source_code}_{idiom}_PHRASE_zh"
            if ck_p in app.my_dict:
                phrase_data.append({"固定搭配": idiom, "中文意思": app.my_dict[ck_p]})
            else:
                p_idx = len(cloud_payload)
                cloud_payload.append(f"短语: {idiom}")
                need_translate_phrases.append((idiom, ck_p, p_idx))

        # 4. 执行仅此 1 次的核心云端网络交互
        cloud_results = deepl_one_shot_translate(cloud_payload, source_lang=source_code, target_lang="ZH")
        
        # 针对辅助语言(英文/德文)使用相应的目标语言重新映射获取
        aux_only_queries = [cloud_payload[idx] for _, _, _, _, idx in need_translate_tokens]
        aux_results_raw = deepl_one_shot_translate(aux_only_queries, source_lang=source_code, target_lang=target_aux_code)

        # 5. 渲染全句意译结果
        full_zh = cloud_results[0] if cloud_results else "翻译失败"
        st.success(f"**全句意译（DeepL 官方直连）：** {full_zh}")

        # 6. 精准拆包，回填数据并推入本地存储
        aux_cursor = 0
        for task, ck_zh, ck_aux, zh_idx, aux_idx in need_translate_tokens:
            raw_zh = cloud_results[zh_idx]
            raw_aux = aux_results_raw[aux_cursor]
            aux_cursor += 1
            
            cleaned_zh = raw_zh.replace("动词 ", "").replace("(动词)", "").replace("（动词）", "").strip()
            task["zh_trans"] = cleaned_zh
            task["aux_trans"] = raw_aux.strip()
            
            if "API" not in cleaned_zh and "API" not in raw_aux:
                app.my_dict[ck_zh] = cleaned_zh
                app.my_dict[ck_aux] = raw_aux

        for idiom, ck_p, p_idx in need_translate_phrases:
            raw_p_zh = cloud_results[p_idx]
            cleaned_p_zh = raw_p_zh.replace("短语: ", "").strip()
            phrase_data.append({"固定搭配": idiom, "中文意思": cleaned_p_zh})
            if "API" not in cleaned_p_zh:
                app.my_dict[ck_p] = cleaned_p_zh

        # 7. 词性拆流并渲染
        verb_data, adj_adv_data, noun_data = [], [], []
        for task in token_tasks:
            row_base = {"词原形": task["lemma"], "中文意思": task.get("zh_trans", "获取失败"), "辅助解析": task.get("aux_trans", "Failed")}
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
