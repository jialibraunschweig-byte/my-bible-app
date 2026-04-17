import streamlit as st
import spacy
import os
import json
import re
from deep_translator import GoogleTranslator

# --- 1. 模型加载 (适配 requirements.txt 预装方式) ---
@st.cache_resource
def load_nlp():
    # 此时假设 requirements.txt 已经通过链接安装了 de_core_news_sm
    return spacy.load("de_core_news_sm")

nlp = load_nlp()

# --- 2. 词典管理 (Streamlit 环境) ---
dict_path = "my_dict.json"

def load_dict():
    if os.path.exists(dict_path):
        with open(dict_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_dict(data):
    with open(dict_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 3. 网页界面设计 ---
st.set_page_config(page_title="德中圣经解析器", layout="wide")
st.title("📖 德中圣经逐词解析")
st.info("功能：自动过滤 HFA 索引、跳过章节号、清理括号内容、生成语法原型表。")

# 获取当前词典
my_dict = load_dict()
translator = GoogleTranslator(source='de', target='zh-CN')

# 输入框
raw_input = st.text_area("请粘贴原文内容:", height=150, placeholder="例如: Prediger 12:5 HFA 5 Du fürchtest dich...")

if st.button("开始解析翻译"):
    if raw_input.strip():
        # --- A. 过滤 HFA 及其后的数字 ---
        sentence = raw_input
        if "HFA" in raw_input:
            parts = raw_input.split("HFA", 1)
            after_hfa = parts[1]
            # 寻找 HFA 后的第一个数字（章节号）
            digit_match = re.search(r'\d+', after_hfa)
            if digit_match:
                sentence = after_hfa[digit_match.end():].strip()
            else:
                sentence = after_hfa.strip()

        # --- B. 删除括号内的内容 ---
        # 清理 () 和 [] 及其内部文字
        sentence = re.sub(r'\(.*?\)|\[.*?\]', '', sentence)
        # 清理可能产生的双空格
        sentence = re.sub(r'\s+', ' ', sentence).strip()

        if not sentence:
            st.error("❌ 无法识别有效正文，请检查输入格式。")
        else:
            with st.spinner('正在处理中...'):
                # 1. 全句翻译
                try:
                    full_trans = translator.translate(sentence)
                except:
                    full_trans = "[翻译接口超时，请稍后再试]"

                # 展示翻译结果
                st.subheader("💡 全句对译")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**德语原文:**\n> {sentence}")
                with col2:
                    st.success(f"**中文翻译:**\n\n{full_trans}")

                # 2. 逐词解析 (Spacy)
                doc = nlp(sentence)
                analysis_data = []

                for token in doc:
                    # 跳过标点和空格
                    if token.is_punct or token.is_space:
                        continue
                    
                    lemma = token.lemma_
                    pos = token.pos_

                    # 翻译单词原型 (优先查词典)
                    if lemma in my_dict:
                        word_trans = my_dict[lemma]
                    else:
                        try:
                            word_trans = translator.translate(lemma)
                            my_dict[lemma] = word_trans
                        except:
                            word_trans = "[超时]"
                    
                    analysis_data.append({
                        "德语原词": token.text,
                        "对应汉语": word_trans,
                        "德语原型": f"{lemma} ({pos})"
                    })

                # 3. 显示结果表格
                st.subheader("🔍 逐词语法分析")
                st.table(analysis_data)

                # 4. 生成 Markdown 笔记供复制
                st.subheader("📝 笔记导出 (Markdown)")
                note_md = f"### 经文解析\n- **原文**: {sentence}\n- **翻译**: {full_trans}\n\n"
                note_md += "| 德语原词 | 对应汉语 | 德语原型 |\n| :--- | :--- | :--- |\n"
                for item in analysis_data:
                    note_md += f"| {item['德语原词']} | {item['对应汉语']} | {item['德语原型']} |\n"
                
                st.code(note_md, language="markdown")
                
                # 保存词典更新
                save_dict(my_dict)
    else:
        st.warning("请先粘贴内容再点击按钮。")
