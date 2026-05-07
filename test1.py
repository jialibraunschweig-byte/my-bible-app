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

# --- 2. 核心翻译逻辑：增加语境引导 ---
def smart_translate(text, pos, source_lang="de"):
    try:
        if source_lang == "de":
            if pos == "VERB":
                # 针对动词，引导翻译引擎进入“行为/法律”语境
                query = f"Bedeutung vom Verb '{text}' im Sinne von Gesetz oder Handlung"
            elif pos == "PHRASE":
                query = f"Was bedeutet die Redewendung '{text}'?"
            else:
                query = text
            
            raw_res = GoogleTranslator(source='de', target='zh-CN').translate(query)
            # 清理冗余的引导词
            return raw_res.replace("的意思是", "").replace("含义是", "").split("：")[-1].strip()
        else:
            return GoogleTranslator(source=source_lang, target='zh-CN').translate(text)
    except:
        return "翻译超时"

def clear_text():
    st.session_state["input_sentence"] = ""

st.title("📖 德语经文精准解析器 (雅各书 2:11 修复版)")
st.caption("核心改进：修正 übertreten, umbringen 等动词的原形还原错误")

# --- UI 布局 ---
lang_option = st.radio("选择语言:", ("德语 (Deutsch)", "英语 (English)"), horizontal=True)
source_code = "de" if "德语" in lang_option else "en"
target_aux_code = "en" if source_code == "de" else "de"

sentence = st.text_area("请粘贴德语内容:", key="input_sentence", height=150)

col1, col2 = st.columns([1, 5])
with col1:
    parse_btn = st.button("开始深度解析")
with col2:
    st.button("清除内容", on_click=clear_text)

GERMAN_PREFIXES = {"ab", "an", "auf", "aus", "bei", "ein", "empor", "entgegen", "fest", "fort", "her", "hin", "los", "nach", "nieder", "vor", "weg", "weiter", "zu", "zurück", "zusammen", "um"}

if parse_btn and sentence:
    with st.spinner('正在分析语法并修正词形还原...'):
        nlp = get_nlp(source_code)
        doc = nlp(sentence)
        
        # 全句翻译
        full_zh = GoogleTranslator(source=source_code, target='zh-CN').translate(sentence)
        st.success(f"**全句意译：** {full_zh}")

        verb_data, adj_adv_data, noun_data, phrase_data = [], [], [], []
        processed_keys = set()

        # 预处理可分前缀
        particles_map = {}
        for token in doc:
            if token.dep_ == "svp":
                particles_map[token.head.i] = token.text.lower()

        # --- 遍历解析 ---
        for token in doc:
            # 过滤不需要的成分
            if token.is_punct or token.is_space or token.pos_ in ["PRON", "DET", "CONJ", "SCONJ", "PART"]:
                continue
            
            if token.pos_ in ["VERB", "AUX", "ADJ", "ADV", "NOUN", "PROPN"]:
                lemma = token.lemma_.lower()
                original_text = token.text
                
                # --- 核心修正逻辑 ---
                if source_code == "de":
                    # 1. 修正 spaCy 的误判 (如 übertreen -> übertreten)
                    if lemma.endswith("een") and not lemma.endswith("gehen"):
                        # 如果原词包含 'et', 尝试补回
                        if "et" in original_text.lower():
                            lemma = lemma.replace("een", "eten")
                        else:
                            lemma = original_text.lower() # 兜底：使用原始词
                    
                    # 2. 修正 brichst -> brichsen 这种错误，手动设为 brechen
                    if original_text.lower() == "brichst":
                        lemma = "brechen"

                    # 3. 合并可分动词 (如 um + bringen)
                    if token.i in particles_map:
                        prefix = particles_map[token.i]
                        if not lemma.startswith(prefix):
                            lemma = prefix + lemma
                
                # 缓存与翻译
                cache_key = f"{lemma}_{token.pos_}"
                if cache_key not in processed_keys:
                    zh_trans = smart_translate(lemma, token.pos_, source_code)
                    aux_trans = GoogleTranslator(source=source_code, target=target_aux_code).translate(lemma)
                    
                    row = {"词原形": lemma, "中文意思": zh_trans, "辅助语言": aux_trans}
                    
                    if token.pos_ in ["VERB", "AUX"]:
                        verb_data.append({"经文动词": original_text, **row})
                    elif token.pos_ in ["NOUN", "PROPN"]:
                        noun_data.append({"经文名词": original_text, **row})
                    else:
                        adj_adv_data.append({"经文原词": original_text, "词类": "形/副", **row})
                    
                    processed_keys.add(cache_key)

        # --- 固定搭配提取 ---
        processed_phrases = set()
        for token in doc:
            if token.pos_ == "VERB":
                for child in token.children:
                    if child.dep_ in ["prep", "obl"]:
                        prep = child.text.lower()
                        if child.pos_ == "ADP":
                            idiom = f"{prep} etwas {token.lemma_}"
                            # 同样修正短语中的误判
                            idiom = idiom.replace("übertreen", "übertreten")
                            if idiom not in processed_phrases:
                                zh_idiom = smart_translate(idiom, "PHRASE", source_code)
                                phrase_data.append({"固定搭配": idiom, "中文意思": zh_idiom})
                                processed_phrases.add(idiom)

        # --- 展示表格 ---
        if phrase_data:
            st.subheader("🚀 固定搭配解析")
            st.table(phrase_data)
        
        t1, t2, t3 = st.tabs(["动词解析", "名词解析", "形容词/副词"])
        with t1: st.table(verb_data)
        with t2: st.table(noun_data)
        with t3: st.table(adj_adv_data)

        app.save_dict()
