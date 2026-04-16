import spacy
import json
import os
import re
import sys
from deep_translator import GoogleTranslator

# 1. 加载语法模型
try:
    nlp = spacy.load("de_core_news_sm")
except:
    import os
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
        print("   德中圣经逐词解析程序 (全能兼容版)")
        print("=" * 60)
        print("说明：直接粘贴全文。如果程序没反应，请按一次回车。输入 'q' 退出。")

        while True:
            print("\n请粘贴原文并回车:")
            
            # 修改点：使用 readlines 逻辑或循环捕捉，但针对粘贴优化
            lines = []
            while True:
                line = sys.stdin.readline()
                if not line or line.strip().lower() == 'q':
                    if not lines: return
                    break
                lines.append(line)
                # 如果这一行不是以换行符结尾，或者缓冲区已空，说明粘贴结束
                if not sys.stdin.isatty() or line.endswith('\n'):
                    # 这是一个针对大多数终端粘贴行为的技巧
                    # 如果读取的内容里已经包含了 HFA 和后续文字，我们就跳出循环
                    combined = "".join(lines)
                    if "HFA" in combined and re.search(r'\d+', combined.split("HFA")[1]):
                        break
                    if not line.strip(): break

            raw_input = " ".join(lines).replace('\n', ' ').strip()
            if not raw_input: continue

            # --- 核心过滤逻辑 ---
            sentence = raw_input
            if "HFA" in raw_input:
                parts = raw_input.split("HFA", 1)
                after_hfa = parts[1]
                digit_match = re.search(r'\d+', after_hfa)
                if digit_match:
                    sentence = after_hfa[digit_match.end():].strip()
                else:
                    sentence = after_hfa.strip()
            
            if not sentence:
                print("❌ 识别失败，请确保粘贴内容包含 HFA 及其后的正文。")
                continue

            print("\n[正在解析中...]")
            doc = nlp(sentence)

            try:
                full_translation = self.translator.translate(sentence)
            except:
                full_translation = "[全句翻译失败]"

            # 构建笔记
            note_content = (
                f"### 经文解析\n"
                f"**DE:** {sentence}\n"
                f"**CN:** {full_translation}\n\n"
                f"| 德语原词 | 对应汉语 | 德语原型 |\n"
                f"| :--- | :--- | :--- |\n"
            )

            print(f"\n[解析结果]\n整句翻译: {full_translation}\n")
            print(f"{'德语原词':<18} | {'对应汉语':<18} | {'德语原型'}")
            print("-" * 75)

            for token in doc:
                if token.is_punct or token.is_space: continue
                lemma = token.lemma_
                pos = token.pos_

                if lemma in self.my_dict:
                    trans = self.my_dict[lemma]
                else:
                    try:
                        trans = self.translator.translate(lemma)
                        self.my_dict[lemma] = trans
                    except:
                        trans = "[超时]"

                proto_info = f"{lemma} ({pos})"
                print(f"{token.text:<18} | {trans:<18} | {proto_info}")
                note_content += f"| {token.text} | {trans} | {proto_info} |\n"

            self.save_dict()
            self.save_note(note_content)
            print(f"\n✅ 解析已成功保存。")

if __name__ == "__main__":
    app = BibleLearningApp()
    app.run()
