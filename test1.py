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
st.set_page_config(page_title="经文翻译助手", layout="centered")

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

def clear_text():
    st.session_state["input_sentence"] = ""

st.title("📖 经文翻译助手")
st.caption("精准版：修复了 mit 等介词被误粘合到动词上的问题")

# --- 语言选择 ---
lang_option = st.radio("请选择输入语言:", ("德语 (Deutsch)", "英语 (English)"), horizontal=True)
source_code = "de" if "德语" in lang_option else "en"

sentence = st.text_area("请粘贴经文内容:", key="input_sentence", height=150)

col1, col2 = st.columns([1, 5])
with col1:
    parse_btn = st.button("开始提取")
with col2:
    st.button("清除内容", on_click=clear_text)

# --- 德语常见分离前缀白名单 ---
# 移除了容易产生误判的简单介词，除非它们确实有分离前缀的语法标记
GERMAN_PREFIXES = {
    "ab", "an", "auf", "aus", "bei", "ein", "empor", "entgegen", 
    "fest", "fort", "her", "herauf", "heraus", "herein", "hin", "hinauf", 
    "hinaus", "hinein", "los", "nach", "nieder", "vor", "voran", 
    "voraus", "vorbei", "weg", "weiter", "zu", "zurück", "zusammen"
}

if parse_btn:
    if sentence:
        with st.spinner('正在分析语法...'):
            nlp = get_nlp(source_code)
            doc = nlp(sentence)
            
            translator_zh = GoogleTranslator(source=source_code, target='zh-CN')
            translator_en = GoogleTranslator(source='de', target='en') if source_code == "de" else None
            
            full_zh = translator_zh.translate(sentence)
            st.success(f"**中文意译：** {full_zh}")

            verb_data = []
            adj_adv_data = []
            
            particles_map = {} 
            if source_code == "de":
                for token in doc:
                    # 核心修改：只有被标记为 svp (分离前缀) 且在白名单中的词才会被粘合
                    # 像 "mit Wein" 里的 mit，其 dep_ 通常是 'case' 而不是 'svp'
                    if token.dep_ == "svp" and token.text.lower() in GERMAN_PREFIXES:
                        verb_idx = token.head.i
                        if verb_idx not in particles_map:
                            particles_map[verb_idx] = []
                        particles_map[verb_idx].append((token.text.lower(), token.i))

            used_particle_indices = [idx for p_list in particles_map.values() for text, idx in p_list]

            for token in doc:
                if token.is_punct or token.is_space or token.i in used_particle_indices:
                    continue
                
                if token.pos_ in ["VERB", "AUX", "ADJ", "ADV"]:
                    # 对于 aufzuheitern，lemma_ 已经是 aufheitern，不需要额外粘合
                    lemma = token.lemma_
                    original_text = token.text

                    # 只有在特定的分离前缀情况下才手动粘合（比如 wiesen ... ab）
                    if source_code == "de" and token.i in particles_map:
                        prefixes = [p[0] for p in particles_map[token.i]]
                        # 检查 lemma 是否已经包含了前缀 (避免重复粘合)
                        if not any(lemma.startswith(p) for p in prefixes):
                            lemma = "".join(prefixes) + lemma
                        original_text = f"{token.text} ... {' '.join(prefixes)}"

                    cache_key = f"{source_code}_{lemma}_v4" 
                    if cache_key in app.my_dict:
                        trans_info = app.my_dict[cache_key]
                    else:
                        try:
                            zh_val = translator_zh.translate(lemma)
                            en_val = translator_en.translate(lemma) if translator_en else None
                            trans_info = {"zh": zh_val, "en": en_val}
                            app.my_dict[cache_key] = trans_info
                        except:
                            trans_info = {"zh": "超时", "en": "超时"}

                    row_data = {"词原形": lemma, "中文意思": trans_info["zh"]}
                    if trans_info["en"]: row_data["英语解释"] = trans_info["en"]

                    if token.pos_ in ["VERB", "AUX"]:
                        verb_data.append({"经文动词": original_text, **row_data})
                    elif token.pos_ in ["ADJ", "ADV"]:
                        # 确保像 mit 这样的介词不会跑进形容词表
                        adj_adv_data.append({"经文原词": token.text, "词类": "形容词" if token.pos_ == "ADJ" else "副词", **row_data})

            if verb_data:
                st.subheader("🔍 动词对照表")
                st.table(verb_data)
            if adj_adv_data:
                st.subheader("🔍 形容词 & 副词对照表")
                st.table(adj_adv_data)
            
            app.save_dict()
    else:
        st.warning("请先粘贴内容。")
