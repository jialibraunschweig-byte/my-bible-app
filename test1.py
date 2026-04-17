import streamlit as st
import json
import os
import re
from deep_translator import GoogleTranslator

# 页面配置
st.set_page_config(page_title="德中圣经学习", layout="centered")


class BibleWebApp:
    def __init__(self, dict_path="my_dict.json", note_path="bible_notes.md"):
        self.dict_path = dict_path
        self.note_path = note_path
        # 初始化词典
        if not os.path.exists(self.dict_path):
            with open(self.dict_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

        with open(self.dict_path, "r", encoding="utf-8") as f:
            self.my_dict = json.load(f)

        self.translator = GoogleTranslator(source='de', target='zh-CN')

    def save_dict(self):
        with open(self.dict_path, "w", encoding="utf-8") as f:
            json.dump(self.my_dict, f, ensure_ascii=False, indent=4)

    def clean_word(self, word):
        return re.sub(r'[^\w\s]', '', word)


# 初始化应用
app = BibleWebApp()

st.title("📖 德中圣经逐词解析")
st.caption("粘贴德语经文，自动生成逐词对照表")

# 输入框
sentence = st.text_area("请粘贴德语经文:", placeholder="例如：Denn Gott hat die Welt so sehr geliebt...")

if st.button("开始解析"):
    if sentence:
        with st.spinner('正在翻译解析中...'):
            # 1. 全句翻译
            full_trans = app.translator.translate(sentence)
            st.success(f"**全句翻译：** {full_trans}")

            # 2. 逐词解析
            words = sentence.split()
            table_data = []

            for raw_word in words:
                word = app.clean_word(raw_word)
                if not word: continue

                word_key = word.lower()
                if word_key in app.my_dict:
                    trans = app.my_dict[word_key]
                else:
                    try:
                        trans = app.translator.translate(word)
                        app.my_dict[word_key] = trans
                    except:
                        trans = "超时"

                table_data.append({"原词": raw_word, "对应汉语": trans, "备注": "自动翻译"})

            # 3. 显示表格
            st.table(table_data)

            # 保存词典
            app.save_dict()

            # 4. 导出笔记功能
            note_text = f"### 经文解析\n**DE:** {sentence}\n**CN:** {full_trans}\n\n| 原词 | 翻译 | 备注 |\n|---|---|---|\n"
            for row in table_data:
                note_text += f"| {row['原词']} | {row['对应汉语']} | - |\n"

            st.download_button("下载本次笔记 (.md)", note_text, file_name="bible_note.md")
    else:
        st.warning("请先粘贴经文内容。")
