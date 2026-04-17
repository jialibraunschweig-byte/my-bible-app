import spacy
import json
import os
import re
from deep_translator import GoogleTranslator

# 1. 自动检查并加载模型
try:
    nlp = spacy.load("de_core_news_sm")
except:
    import os
    print("[系统提示] 正在初始化德语语法引擎...")
    os.system("python -m spacy download de_core_news_sm")
    nlp = spacy.load("de_core_news_sm")


class BibleLearningApp:
    def __init__(self, dict_path="my_dict.json", note_path="bible_notes.md"):
        self.dict_path = dict_path
        self.note_path = note_path
        self.my_dict = self.load_dict()
        self.translator = GoogleTranslator(source='de', target='zh-CN')

    def load_dict(self):
        if os.path.exists(self.dict_path):
            with open(self.dict_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_dict(self):
        with open(self.dict_path, "w", encoding="utf-8") as f:
            json.dump(self.my_dict, f, ensure_ascii=False, indent=4)

    def save_note(self, content):
        with open(self.note_path, "a", encoding="utf-8") as f:
            f.write(content + "\n\n---\n\n")

    def run(self):
        print("\n" + "=" * 60)
        print("   德中圣经逐词解析程序 (括号自动清理版)")
        print("=" * 60)
        print("输入 'q' 退出。")

        while True:
            ref = input("\n请输入经文索引 (如 Prediger 10:4): ")
            if ref.lower() == 'q': break

            raw_sentence = input("请粘贴德语原文: ").strip()
            if raw_sentence.lower() == 'q': break
            if not raw_sentence: continue

            # --- 核心修改：删除括号及其内部的内容 ---
            # 这里的正则表达式会删除 () 和 [] 及其包含的所有内容
            sentence = re.sub(r'\(.*?\)|\[.*?\]', '', raw_sentence)
            # 顺便清理一下可能出现的双空格
            sentence = re.sub(r'\s+', ' ', sentence).strip()

            doc = nlp(sentence)

            # 1. 全句翻译
            try:
                full_translation = self.translator.translate(sentence)
            except:
                full_translation = "[全句翻译失败]"

            # 2. 构建笔记内容
            note_content = (
                f"### {ref}\n"
                f"**DE (已清理括号):** {sentence}\n"
                f"**CN:** {full_translation}\n\n"
                f"| 德语原词 | 对应汉语 | 德语原型 |\n"
                f"| :--- | :--- | :--- |\n"
            )

            # 3. 逐词解析并打印
            print(f"\n[解析结果 - {ref}]")
            print(f"原始输入: {raw_sentence}")
            print(f"清理后经文: {sentence}")
            print(f"整句翻译: {full_translation}\n")

            # 终端表头
            print(f"{'德语原词':<18} | {'对应汉语':<18} | {'德语原型'}")
            print("-" * 75)

            for token in doc:
                if token.is_punct or token.is_space: continue

                lemma = token.lemma_
                pos = token.pos_

                # 获取词典翻译
                if lemma in self.my_dict:
                    trans = self.my_dict[lemma]
                else:
                    try:
                        trans = self.translator.translate(lemma)
                        self.my_dict[lemma] = trans
                    except:
                        trans = "[超时]"

                # 构造德语原型信息
                proto_info = f"{lemma} ({pos})"

                # 终端打印
                print(f"{token.text:<18} | {trans:<18} | {proto_info}")

                # 写入笔记内容
                row = f"| {token.text} | {trans} | {proto_info} |"
                note_content += row + "\n"

            # 4. 保存
            self.save_dict()
            self.save_note(note_content)
            print(f"\n[OK] 解析已保存至 {self.note_path}")


if __name__ == "__main__":
    app = BibleLearningApp()
    app.run()
