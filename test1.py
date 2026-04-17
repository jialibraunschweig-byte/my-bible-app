import json
import os
import re
from deep_translator import GoogleTranslator

class BibleAppMobile:
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

    def clean_word(self, word):
        # 简单去除标点
        return re.sub(r'[^\w\s]', '', word)

    def run(self):
        print("\n" + "=" * 40)
        print("   德中圣经逐词解析 (手机轻量版)")
        print("=" * 40)
        print("输入 'q' 退出程序。")

        while True:
            # 修改点：直接询问经文内容
            sentence = input("\n请粘贴德语经文: ").strip()
            
            if sentence.lower() == 'q': 
                break
            if not sentence: 
                continue

            print("\n[翻译中...]")
            
            # 1. 获取全句翻译
            try:
                full_trans = self.translator.translate(sentence)
            except:
                full_trans = "[翻译连接失败]"

            # 2. 简单分词处理
            words = sentence.split()
            
            # 修改点：笔记标题固定为“经文解析”或原文前几个词
            note_content = (
                f"### 经文解析\n**DE:** {sentence}\n"
                f"**CN:** {full_trans}\n\n"
                f"| 德语原词 | 对应汉语 | 备注 |\n"
                f"| :--- | :--- | :--- |\n"
            )

            print(f"\n整句翻译: {full_trans}\n")
            print(f"{'原词':<15} | {'翻译':<15} | {'备注'}")
            print("-" * 50)

            for raw_word in words:
                word = self.clean_word(raw_word)
                if not word: continue

                # 查词典或在线翻译
                word_key = word.lower()
                if word_key in self.my_dict:
                    trans = self.my_dict[word_key]
                else:
                    try:
                        trans = self.translator.translate(word)
                        self.my_dict[word_key] = trans
                    except:
                        trans = "[超时]"

                print(f"{raw_word:<15} | {trans:<15} | (自动)")
                note_content += f"| {raw_word} | {trans} | - |\n"

            self.save_dict()
            self.save_note(note_content)
            print(f"\n[OK] 笔记已保存至 {self.note_path}")

if __name__ == "__main__":
    app = BibleAppMobile()
    app.run()
