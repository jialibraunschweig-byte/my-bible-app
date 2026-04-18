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
st.caption("终极增强版：解决德语分离动词（如 wiesen ... ab）的强力粘合解析")

# --- 语言选择 ---
lang_option = st.radio("请选择输入语言:", ("德语 (Deutsch)", "英语 (English)"), horizontal=True)
source_code = "de" if "德语" in lang_option else "en"

sentence = st.text_area("请粘贴经文内容:", key="input_sentence", height=150)

col1, col2 = st.columns([1, 5])
with col1:
    parse_btn = st.button("开始提取")
with col2:
    st.button("清除内容", on_click=clear_text)

if parse_btn:
    if sentence:
        with st.spinner('正在执行深度语法重组...'):
            nlp = get_nlp(source_code)
            doc = nlp(sentence)
            
            # 初始化翻译器
            translator_zh = GoogleTranslator(source=source_code, target='zh-CN')
            translator_en = GoogleTranslator(source='de', target='en') if source_code == "de" else None
            
            full_zh = translator_zh.translate(sentence)
            st.success(f"**中文意译：** {full_zh}")

            verb_data = []
            adj_adv_data = []
            
            # --- 核心改进：手动寻找分离前缀 ---
            particles_map = {} # 格式: {动词索引: [前缀文本, 前缀索引]}
            
            if source_code == "de":
                for token in doc:
                    # 寻找分离前缀：1. 语法标注为 svp 的； 2. 位于末尾指向动词的副词或介词
                    if token.dep_ == "svp" or (token.pos_ in ["ADP", "ADV"] and token.head.pos_ == "VERB"):
                        verb_idx = token.head.i
                        if verb_idx not in particles_map:
                            particles_map[verb_idx] = []
                        particles_map[verb_idx].append((token.text.lower(), token.i))

            used_particle_indices = [idx for p_list in particles_map.values() for text, idx in p_list]

            for token in doc:
                if token.is_punct or token.is_space or token.i in used_particle_indices:
                    continue
                
                if token.pos_ in ["VERB", "AUX", "ADJ", "ADV"]:
                    lemma = token.lemma_
                    original_text = token.text

                    # --- 强力粘合逻辑 ---
                    if source_code == "de" and token.i in particles_map:
                        # 拿到所有属于该动词的前缀
                        prefixes = [p[0] for p in particles_map[token.i]]
                        # 将前缀拼在原形前面，例如 ab + weisen = abweisen
                        # 我们按照词序最后出现的通常是前缀，将其拼在 lemma 最前面
                        combined_lemma = "".join(prefixes) + lemma
                        lemma = combined_lemma
                        original_text = f"{token.text} ... {' '.join(prefixes)}"

                    # 缓存与翻译
                    cache_key = f"{source_code}_{lemma}_v2" # 更新缓存版本
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
                        adj_adv_data.append({"经文原词": token.text, "词类": "形容词" if token.pos_ == "ADJ" else "副词", **row_data})

            if verb_data:
                st.subheader("🔍 动词对照表 (已强力粘合分离动词)")
                st.table(verb_data)
            if adj_adv_data:
                st.subheader("🔍 形容词 & 副词对照表")
                st.table(adj_adv_data)
            
            app.save_dict()
    else:
        st.warning("请先粘贴内容。")
