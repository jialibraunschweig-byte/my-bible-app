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

# --- 2. DeepL API ---
DEEPL_API_KEY = "b5b43291-f654-4a84-a0b1-c1d862852987:fx"

def deepl_raw_translate(text, source_lang, target_lang):
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
            return f"暂无译文 (错误码: {response.status_code})"
    except Exception:
        return "网络交互重试中"

def clear_text():
    st.session_state["input_sentence"] = ""

# --- 3. 核心语言清洗与【至高硬编码精准词典】 ---
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

# ⚡【至高无上本地词典】全小写化键名，100%硬核拦截
HARDCODED_TRANSLATION_MAP = {
    # 动词类
    "geben": ("给予、赐予", "give"),
    "stammen": ("源自、出于", "come from / originate"),
    "befähigen": ("赋能、使有能力", "enable / empower"),
    "scheren": ("剪、剃（头发）", "shear / cut"),
    "bewähren": ("证明、经受考验、站稳脚跟", "prove oneself / stand the test"),
    "sagen": ("说、表达", "say / tell"),
    "brauchen": ("需要", "need / require"),
    "erscheinen": ("显得、出现、看来", "appear / seem"),
    # 名词类 (全部规范为小写作为查找键)
    "auge": ("眼睛", "eye"),
    "hand": ("手", "hand"),
    "kopf": ("头、头部", "head"),
    "fuß": ("脚、脚部", "foot"),
    "teil": ("部分、部件、器官", "part / component"),
    "körper": ("身体、肉体", "body"),
    # 形容词/副词
    "leichtfertig": ("轻率、鲁莽、草率", "reckless / frivolous"),
    "gedankenlos": ("不假思索、轻率、粗心", "thoughtlessly"),
    "überflüssig": ("多余的、不必要的", "superfluous / redundant"),
    "schwach": ("软弱的、微弱的", "weak"),
    "unbedeutend": ("微不足道的、不重要的", "insignificant / minor"),
    "wichtig": ("重要的", "important")
}

st.title("📖 德语经文精准解析器")
st.info("💡 强力升级版：内置历史脏缓存污染物理熔断器，彻底粉碎“获取失败”等历史残留。")

lang_option = st.radio("选择语言:", ("德语 (Deutsch)", "英语 (English)"), horizontal=True)
source_code = "de" if "德语" in lang_option else "en"
target_aux_code = "en" if source_code == "de" else "de"

sentence = st.text_area("请粘贴经文内容:", key="input_sentence", height=150)

col1, col2 = st.columns([1, 5])
with col1:
    parse_btn = st.button("开始深度解析")
with col2:
    st.button("清除内容", on_click=clear_text)

if parse_btn and sentence:
    with st.spinner('安全加密通道一体化解析中...'):
        # 全局清洗干扰编号
        clean_sentence = re.sub(r'\[\d+\]', '', sentence)
        clean_sentence = re.sub(r'\b\d+\b', '', clean_sentence)

        nlp = get_nlp(source_code)
        doc = nlp(clean_sentence)

        processed_keys = set()
        token_tasks = []
        particles_map = {token.head.i: token.text.lower() for token in doc if token.dep_ == "svp"}

        # 1. 结构清洗与语法提取
        for token in doc:
            raw_text_clean = re.sub(r'\d+', '', token.text).strip("[] .»«!¡?¿“” ")
            if not raw_text_clean or token.is_punct or token.is_space or token.pos_ in ["PRON", "DET", "CONJ", "SCONJ", "PART", "ADP"]:
                continue

            if token.pos_ in ["VERB", "AUX", "ADJ", "ADV", "NOUN", "PROPN"]:
                original_text = token.text
                original_text_clean = re.sub(r'\[\d+\]', '', original_text).strip(". »«!¡?¿“” ")

                lower_raw = original_text_clean.lower()

                if source_code == "de" and lower_raw in SPECIAL_VERB_LEMMA_MAP:
                    lemma = SPECIAL_VERB_LEMMA_MAP[lower_raw]
                    current_pos = "VERB"
                else:
                    # 统一规范：名词保留原型首字母大写，其余小写
                    lemma = token.lemma_ if token.pos_ in ["NOUN", "PROPN"] else token.lemma_.lower()
                    lemma = re.sub(r'\[\d+\]', '', lemma).strip(". »«!¡?¿“” ")
                    current_pos = token.pos_

                if source_code == "de" and (lemma.lower() in GERMAN_BASIC_VERBS or lower_raw in GERMAN_BASIC_VERBS):
                    continue
                elif source_code == "en" and (lemma.lower() in ENGLISH_BASIC_VERBS or lower_raw in ENGLISH_BASIC_VERBS):
                    continue

                if (lemma.lower() in EXCLUDE_WORDS or lower_raw in EXCLUDE_WORDS) and current_pos == "ADJ":
                    continue

                if source_code == "de" and current_pos == "VERB":
                    if lemma.endswith("een") and not lemma.endswith("gehen"):
                        lemma = lemma.replace("een", "eten") if "et" in lower_raw else lower_raw
                    if token.i in particles_map:
                        prefix = particles_map[token.i]
                        if not lemma.startswith(prefix):
                            lemma = prefix + lemma

                cache_key = f"{lemma}_{current_pos}"
                if cache_key not in processed_keys:
                    token_tasks.append({"original_text": original_text_clean, "lemma": lemma, "pos": current_pos})
                    processed_keys.add(cache_key)

        # 2. 提取德语可拆分动词固定搭配
        phrase_tasks = []
        processed_phrases = set()
        if source_code == "de":
            for token in doc:
                if token.pos_ == "VERB" and token.lemma_.lower() not in GERMAN_BASIC_VERBS:
                    for child in token.children:
                        if child.dep_ in ["prep", "obl", "prt"] and child.pos_ in ["ADP", "PART"]:
                            v_lemma = SPECIAL_VERB_LEMMA_MAP.get(token.text.lower(), token.lemma_.lower())
                            idiom = f"{child.text.lower()} etwas {v_lemma}"
                            if idiom not in processed_phrases:
                                phrase_tasks.append(idiom)
                                processed_phrases.add(idiom)

        # 3. 翻译大句
        full_zh = deepl_raw_translate(clean_sentence, source_lang=source_code, target_lang="ZH")
        st.success(f"**全句意译（DeepL 官方直连）：** {full_zh}")

        # 4. 固定搭配数据组装
        phrase_data = []
        for idiom in phrase_tasks:
            ck_p = f"{source_code}_{idiom}_PHRASE_zh"
            # 脏缓存物理清洗保护
            if ck_p in app.my_dict and "获取失败" not in str(app.my_dict[ck_p]) and "暂无" not in str(app.my_dict[ck_p]):
                p_zh = app.my_dict[ck_p]
            else:
                p_zh = deepl_raw_translate(idiom, source_lang=source_code, target_lang="ZH")
                if p_zh and "暂无" not in p_zh and "429" not in p_zh:
                    app.my_dict[ck_p] = p_zh
            phrase_data.append({"固定搭配": idiom, "中文意思": p_zh})

        verb_data, adj_adv_data, noun_data = [], [], []

        for task in token_tasks:
            lemma_lower = task["lemma"].lower()
            ck_zh  = f"{source_code}_{task['lemma']}_{task['pos']}_zh"
            ck_aux = f"{source_code}_{task['lemma']}_{task['pos']}_aux"

            # 🛠️ 历史脏缓存污染物理熔断器：如果旧缓存在本地包含“获取失败”或“将德语”，立刻物理清除！
            if ck_zh in app.my_dict:
                old_val = str(app.my_dict[ck_zh])
                if "获取失败" in old_val or "将德语" in old_val or "Translate" in old_val or "、手、" in old_val:
                    del app.my_dict[ck_zh]
            if ck_aux in app.my_dict:
                old_aux = str(app.my_dict[ck_aux])
                if "Translate" in old_aux or "获取失败" in old_aux:
                    del app.my_dict[ck_aux]

            # 🥇 第一层防御：判定至高无上硬编码本地词典 (彻底屏蔽网络抖动和大小写偏差)
            if lemma_lower in HARDCODED_TRANSLATION_MAP:
                zh_trans, aux_trans = HARDCODED_TRANSLATION_MAP[lemma_lower]
            # 🥈 第二层防御：从干净的本地历史缓存读取
            elif ck_zh in app.my_dict and ck_aux in app.my_dict:
                zh_trans = app.my_dict[ck_zh]
                aux_trans = app.my_dict[ck_aux]
            # 🥉 第三层防御：纯净单词直连 DeepL 单查
            else:
                # 查中文
                zh_trans = deepl_raw_translate(task["lemma"], source_lang=source_code, target_lang="ZH")
                # 查辅助语言（EN）
                aux_trans = deepl_raw_translate(task["lemma"], source_lang=source_code, target_lang=target_aux_code)

                # 清洗边缘多余句点与引号
                zh_trans = zh_trans.strip(' ."“”\'\'«»').replace("将德语单词", "").replace("翻译成中文", "")
                aux_trans = aux_trans.strip(' ."“”\'\'«»')

                # 兜底清洗：若被复读，做无害化处理
                if "translate" in zh_trans.lower() or zh_trans.lower() == task["lemma"].lower() or "获取失败" in zh_trans:
                    zh_trans = "暂无译文"
                if "translate" in aux_trans.lower() or aux_trans.lower() == task["lemma"].lower() or "failed" in aux_trans.lower():
                    aux_trans = "Failed"

                # 写入清洗过后的健康字典
                if zh_trans != "暂无译文" and aux_trans != "Failed" and "429" not in zh_trans:
                    app.my_dict[ck_zh] = zh_trans
                    app.my_dict[ck_aux] = aux_trans

            # 分包渲染
            row_base = {
                "词原形":  task["lemma"],
                "中文意思": zh_trans,
                "辅助解析": aux_trans
            }

            if task["pos"] in ["VERB", "AUX"]:
                verb_data.append({"经文动词": task["original_text"], **row_base})
            elif task["pos"] in ["NOUN", "PROPN"]:
                noun_data.append({"经文名词": task["original_text"], **row_base})
            else:
                adj_adv_data.append({"经文原词": task["original_text"], **row_base})

        # 5. 页面数据表格渲染
        if phrase_data:
            st.subheader("🚀 固定搭配解析")
            st.table(phrase_data)

        t1, t2, t3 = st.tabs(["动词解析", "名词解析", "形容词/副词"])
        with t1: st.table(verb_data)
        with t2: st.table(noun_data)
        with t3: st.table(adj_adv_data)

        app.save_dict()
