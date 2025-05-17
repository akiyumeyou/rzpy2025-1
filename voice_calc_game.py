#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import subprocess
import time
from conversation_manager import ConversationManager
from speech_output import speak
from datetime import datetime
from file_operations import save_calc_game_result
from speech_input import listen

# 日本語数字→数値変換用辞書
KANJI_NUMS = {
    "ぜろ": 0, "れい": 0, "いち": 1, "に": 2, "さん": 3, "し": 4, "よん": 4, "ご": 5, "ろく": 6, "しち": 7, "なな": 7, "はち": 8, "きゅう": 9, "く": 9,
    "じゅう": 10, "ひゃく": 100
}

def japanese_number_to_int(text):
    """日本語の数字（1〜99程度、マイナス対応、フィラー・空白除去）を数値に変換"""
    if not text:
        raise ValueError("空のテキスト")
    # フィラー語・不要語を除去
    fillers = ["えー", "うーん", "あのー", "えっと", "ええと", "うー", "うん"]
    for f in fillers:
        text = text.replace(f, "")
    # 空白・全角スペース除去
    text = text.replace(" ", "").replace("　", "")
    text = text.replace("一", "いち").replace("二", "に").replace("三", "さん").replace("四", "よん").replace("五", "ご").replace("六", "ろく").replace("七", "なな").replace("八", "はち").replace("九", "きゅう").replace("十", "じゅう").replace("百", "ひゃく")
    is_negative = False
    # マイナス表現の検出
    if text.startswith("まいなす") or text.startswith("マイナス") or text.startswith("-"):
        is_negative = True
        text = text.replace("まいなす", "", 1).replace("マイナス", "", 1).replace("-", "", 1)
    if text.isdigit():
        value = int(text)
    else:
        num = 0
        if "ひゃく" in text:
            idx = text.find("ひゃく")
            if idx == 0:
                num += 100
            else:
                num += KANJI_NUMS.get(text[:idx], 1) * 100
            text = text[idx+3:]
        if "じゅう" in text:
            idx = text.find("じゅう")
            if idx == 0:
                num += 10
            else:
                num += KANJI_NUMS.get(text[:idx], 1) * 10
            text = text[idx+3:]
        if text:
            num += KANJI_NUMS.get(text, 0)
        value = num
    return -value if is_negative else value

class VoiceCalculationGame:
    """音声による計算ゲーム"""
    
    def __init__(self):
        """初期化"""
        self.conversation_manager = ConversationManager()
        
    def speak(self, text):
        print(f"コンピュータ: {text}")
        self.conversation_manager.add_to_conversation("system", text)
        speaking_text = re.sub(r'は[？?]', 'わ？', text)
        subprocess.run(['say', '-v', 'Kyoko', speaking_text])
    
    def generate_question(self, level=1):
        """計算問題を生成（level=1:簡単, level=2:難しい）"""
        if level == 1:
            a = random.randint(1, 9)
            b = random.randint(1, 9)
            operator = random.choice(["+", "-", "*"])
        else:
            operator = random.choice(["+", "-", "*", "/"])
            if operator == "+":
                a = random.randint(10, 99)
                b = random.randint(10, 99)
            elif operator == "-":
                a = random.randint(10, 99)
                b = random.randint(10, a)  # a >= b
            elif operator == "*":
                a = random.randint(2, 12)
                b = random.randint(2, 12)
            else:  # "/"
                b = random.randint(2, 12)
                answer = random.randint(2, 12)
                a = b * answer  # 割り切れるように
        
        if operator == "+":
            answer = a + b
            question = f"{a}たす{b}は？"
        elif operator == "-":
            answer = a - b
            question = f"{a}ひく{b}は？"
        elif operator == "*":
            answer = a * b
            question = f"{a}かける{b}は？"
        else:  # "/"
            question = f"{a}わる{b}は？"
        return question, answer
    
    def run_game(self):
        """ゲームを実行（10問固定、途中経過アナウンス、難易度調整）"""
        speak("計算問題を出しますので、答えを言ってください。")
        speak("全部で10問です。途中でゲームを終了するには、「終了」と言ってください。")
        
        score = 0
        total_questions = 10
        detail_results = []
        start_time = time.time()
        
        for i in range(1, total_questions + 1):
            # 5問目以降は難易度アップ
            level = 1 if i <= 5 else 2
            question, answer = self.generate_question(level=level)
            speak(question)
            print(f"【出題】{question}")  # 問題と正解を表示
            
            response = listen()
            if response is None:
                # もう一度同じ問題を出します。
                speak("もう一度同じ問題を出します。")
                speak(question)
                response = listen()
                if response is None:
                    detail_results.append(f"{i}問目: スキップ")
                    continue
            
            if "終了" in response:
                detail_results.append(f"{i}問目: ユーザーが終了を選択")
                break
            
            try:
                # 日本語数字→数値変換
                user_answer = japanese_number_to_int(response)
                print(f"【ユーザー発話】{response} → 【変換後】{user_answer}")  # 認識結果と変換後数値を表示
                if user_answer == answer:
                    speak("正解です！")
                    score += 1
                    detail_results.append(f"{i}問目: 正解")
                else:
                    speak(f"残念、正解は{answer}でした。")
                    detail_results.append(f"{i}問目: 不正解（答: {answer}）")
            except Exception:
                print(f"【ユーザー発話】{response} → 【変換失敗】")
                speak("数字で答えてください。")
                detail_results.append(f"{i}問目: 無効回答")
                continue
            
            # 5問目と10問目で途中経過をアナウンス
            if i == 5 or i == 10:
                speak(f"{i}問目が終わりました。ここまで{score}問正解です。")
        
        end_time = time.time()
        speak(f"ゲーム終了です。{i}問中{score}問正解でした。")
        speak("お疲れ様でした。")
        
        # Googleスプレッドシート（Sheet2）に記録
        save_calc_game_result(start_time, end_time, score, i, detail_results)

if __name__ == "__main__":
    game = VoiceCalculationGame()
    game.run_game() 