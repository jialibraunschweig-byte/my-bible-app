import streamlit as st
import spacy
import os
import json
import re
from deep_translator import GoogleTranslator

# --- 1. 网页版专用的模型加载方式 (带缓存) ---
@st.cache_resource
def load_nlp():
    try:
        # 尝试加载模型
        return spacy.load("de_core_news_sm")
    except:
        # 如果没有，则下载并加载
        os.system("python -m spacy download de_core_news_sm")
        return spacy.load("de_core_news_sm")

nlp = load_nlp()

# --- 2. 初始化词典 ---
# 注意：在 Streamlit Cloud 上，文件保存是临时的，重启后会重置
dict_path = "my_dict.json"
if not os.path.exists(dict_path):
    with open(dict_path, "w", encoding="utf-8") as f:
        json.dump({}, f)

def load_dict():
    with open(dict_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_dict(data):
    with open(dict_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

my_dict = load_dict()
translator = GoogleTranslator(source='de', target='zh-CN')

# --- 3. 网页界面布局 ---
st.set_page_config(page_title="德中圣经逐词解析", layout="centered")
st.title("📖 德中圣经逐词解析")
st.caption("支持自动过滤 HFA 索引及清理括号内容")

# 输入区域
raw_input = st.text_area("请粘贴德语原文内容:", height=200, placeholder="例如: Prediger 12:13 HFA 13 Zu guter Letzt...")

if st.button("开始解析"):
    if raw_input.strip():
        # --- A. 核心过滤逻辑：HFA 数字后截断 ---
        sentence = raw_input
        if "HFA" in raw_input:
            parts = raw_input.split("HFA", 1)
            after_hfa = parts[1]
            digit_match = re.search(r'\d+', after_hfa)
            if digit_match:
                sentence = after_hfa[digit_match.end():].strip()
            else:
                sentence = after_hfa.strip()

        # --- B. 核心过滤逻辑：删除括号内容 ---
        # 删除 () 和 [] 及其内部内容
        sentence = re.sub(r'\(.*?\)|\[.*?\]', '', sentence)
        sentence = re.sub(r'\s+', ' ', sentence).strip()

        if not sentence:
            st.error("❌ 过滤后未识别到有效德语正文，请检查输入。")
        else:
            with st.spinner('正在解析并翻译中，请稍候...'):
                # 1. 全句翻译
                try:
                    full_trans = translator.translate(sentence)
                except:
                    full_trans = "[翻译超时]"

                st.subheader("🌟 全句翻译")
                st.success(full_trans)

                # 2. 逐词解析
                doc = nlp(sentence)
                table_data = []

                for token in doc:
                    if token.is_punct or token.is_space:
                        continue
                    
                    lemma = token.lemma_
                    pos = token.pos_

                    # 查词或在线翻译
                    if lemma in my_dict:
                        trans = my_dict[lemma]
                    else:
                        try:
                            trans = translator.translate(lemma)
                            my_dict[lemma] = trans
                        except:
                            trans = "[超时]"
                    
                    proto_info = f"{lemma} ({pos})"
                    table_data.append({
                        "德语原词": token.text,
                        "对应汉语": trans,
                        "德语原型": proto_info
                    })

                # 3. 显示结果表格
                st.subheader("📝 逐词对照表")
                st.table(table_data)

                # 保存词典更新
                save_dict(my_dict)

                # 4. 提供 Markdown 笔记下载
                note_text = f"### 经文解析\n**原文:** {sentence}\n**翻译:** {full_trans}\n\n| 原词 | 翻译 | 原型 |\n|---|---|---|\n"
                for row in table_data:
                    note_text += f"| {row['德语原词']} | {row['对应汉语']} | {row['德语原型']} |\n"
                
                st.download_button("📥 下载解析笔记 (.md)", note_text, file_name="bible_note.md")
    else:
        st.warning("⚠️ 请先粘贴经文内容。")
