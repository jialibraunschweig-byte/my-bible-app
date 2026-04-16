import streamlit as st
import re
from deep_translator import GoogleTranslator

st.title("📖 德中圣经解析 (网页版)")

# 输入框
raw_input = st.text_area("请粘贴原文:", placeholder="在这里粘贴带 HFA 的内容...")

if st.button("开始解析"):
    if raw_input:
        # 网页版的过滤逻辑
        sentence = raw_input
        if "HFA" in raw_input:
            parts = raw_input.split("HFA", 1)
            after_hfa = parts[1]
            digit_match = re.search(r'\d+', after_hfa)
            if digit_match:
                sentence = after_hfa[digit_match.end():].strip()
            else:
                sentence = after_hfa.strip()

        # 翻译和显示逻辑...
        st.write(f"**解析正文:** {sentence}")
        trans = GoogleTranslator(source='de', target='zh-CN').translate(sentence)
        st.success(f"**翻译:** {trans}")
    else:
        st.warning("请输入内容")
