import streamlit as st
import json
import os
import spacy
from deep_translator import GoogleTranslator

# --- 1. 模型加载 (针对 Streamlit 优化) ---
@st.cache_resource
def load_nlp():
    try:
        # 尝试加载模型
        return spacy.load("de_core_news_sm")
    except:
        # 如果不存在则下载（备用逻辑）
        os.system("python -m spacy download de_core_news_sm")
        return spacy.load("de_core_news_sm")

nlp = load_nlp()

# 页面配置
st.set_page_config(page_title="德中圣经动词解析", layout="centered")

class BibleWebApp:
    def __init__(self, dict_path="my_dict.json"):
        self.dict_path = dict_path
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

# 初始化应用
app = BibleWebApp()

st.title("📖 德中圣经：动词专项解析")
st.caption("自动识别动词、还原原型并翻译（已去掉备注栏）")

# 输入框
sentence = st.text_area("请粘贴德语经文:", placeholder="例如：Denn Gott hat die Welt so sehr geliebt...")

if st.button("开始解析动词"):
    if sentence:
        with st.spinner('正在识别动词并获取原型...'):
            # 1. 全句翻译
            full_trans = app.translator.translate(sentence)
            st.success(f"**全句意译：** {full_trans}")

            # 2. NLP 动词解析
            doc = nlp(sentence)
            table_data = []

            for token in doc:
                # 只筛选动词 (VERB) 和 助动词 (AUX)
                if token.pos_ in ["VERB", "AUX"]:
                    lemma = token.lemma_  # 动词原型
                    
                    # 使用原型作为 key 查词典或翻译
                    if lemma in app.my_dict:
                        trans = app.my_dict[lemma]
                    else:
                        try:
                            # 翻译原型含义
                            trans = app.translator.translate(lemma)
                            app.my_dict[lemma] = trans
                        except:
                            trans = "超时"

                    # 只保留：经文动词、动词原型、对应汉语
                    table_data.append({
                        "经文动词": token.text,
                        "动词原型": lemma,
                        "对应汉语": trans
                    })

            # 3. 显示结果表格
            if table_data:
                st.subheader("🔍 动词解析表")
                st.table(table_data)
                
                # 保存词典
                app.save_dict()

                # 4. 导出笔记 (Markdown 格式)
                note_text = f"### 经文动词解析\n**DE:** {sentence}\n**CN:** {full_trans}\n\n| 经文动词 | 动词原型 | 对应汉语 |\n|---|---|---|\n"
                for row in table_data:
                    note_text += f"| {row['经文动词']} | {row['动词原型']} | {row['对应汉语']} |\n"
                
                st.download_button("下载动词笔记 (.md)", note_text, file_name="bible_verbs.md")
            else:
                st.info("在该段经文中未识别到动词。")
    else:
        st.warning("请先粘贴经文内容。")
