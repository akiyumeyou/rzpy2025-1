#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import speech_recognition as sr
import subprocess
import time
from conversation_manager import ConversationManager
import unicodedata

class VoiceCalculationGame:
    """音声による計算ゲーム"""
    
    def __init__(self):
        """初期化"""
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.conversation_manager = ConversationManager()
        
        # 環境ノイズの調整
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
    
    def speak(self, text):
        """テキストを音声で読み上げる"""
        print(f"コンピュータ: {text}")
        # 会話を記録
        self.conversation_manager.add_to_conversation("system", text)
        # 「は」を「わ」と発音させるための置換
        speaking_text = text.replace("は", "わ").replace("初めましょう", "はじめましょう")
        # macOSのsayコマンドを使用
        subprocess.run(["say", "-v", "Kyoko", speaking_text])
    
    def listen(self):
        """音声を認識して返す"""
        with self.microphone as source:
            print("聞いています...")
            try:
                audio = self.recognizer.listen(source, timeout=10.0)
                text = self.recognizer.recognize_google(audio, language='ja-JP')
                print(f"認識された発話: {text}")
                # 会話を記録
                self.conversation_manager.add_to_conversation("user", text)
                return text.lower()
            except sr.WaitTimeoutError:
                self.speak("声が聞こえませんでした。もう一度お願いします。")
                return None
            except sr.UnknownValueError:
                self.speak("すみません、聞き取れませんでした。もう一度お願いします。")
                return None
            except sr.RequestError:
                self.speak("音声認識サービスに接続できませんでした。ネットワーク接続を確認してください。")
                return None
    
    def generate_question(self):
        """計算問題を生成"""
        a = random.randint(1, 9)
        b = random.randint(1, 9)
        operator = random.choice(["+", "-", "*"])
        
        if operator == "+":
            answer = a + b
            question = f"{a}たす{b}は？"
        elif operator == "-":
            # 負の数にならないように
            if a < b:
                a, b = b, a
            answer = a - b
            question = f"{a}ひく{b}は？"
        else:  # "*"
            answer = a * b
            question = f"{a}かける{b}は？"
        
        return question, answer
    
    def run_game(self):
        """ゲームを実行"""
        print("\n=== 計算ゲーム開始 ===")
        print("問題が出題されます。答えを言ってください。")
        print("===================\n")
        
        correct_count = 0
        total_questions = 5
        
        for i in range(total_questions):
            # 問題を生成
            num1 = random.randint(1, 10)
            num2 = random.randint(1, 10)
            operator = random.choice(['+', '-', '*'])
            
            # 問題を表示（音声出力なし）
            if operator == '+':
                answer = num1 + num2
                print(f"\n問題 {i+1}/{total_questions}: {num1} + {num2} = ?")
            elif operator == '-':
                answer = num1 - num2
                print(f"\n問題 {i+1}/{total_questions}: {num1} - {num2} = ?")
            else:
                answer = num1 * num2
                print(f"\n問題 {i+1}/{total_questions}: {num1} × {num2} = ?")
            
            # 音声で問題を読み上げ
            if operator == '+':
                self.speak(f"{num1}たす{num2}は？")
            elif operator == '-':
                self.speak(f"{num1}ひく{num2}は？")
            else:
                self.speak(f"{num1}かける{num2}は？")
            
            # ユーザーの回答を待つ
            user_answer = self.listen()
            if user_answer is None:
                continue
            
            # 正解判定
            try:
                if int(normalize_answer(user_answer)) == int(answer):
                    correct_count += 1
                    print("正解です！")
                    self.speak("正解です")
                else:
                    print(f"不正解です。正解は{answer}でした。")
                    self.speak(f"不正解です。正解は{answer}でした。")
            except Exception as e:
                print(f"判定エラー: {e}")
                print(f"不正解です。正解は{answer}でした。")
                self.speak(f"不正解です。正解は{answer}でした。")
        
        # 結果を表示（音声出力なし）
        print("\n=== ゲーム結果 ===")
        print(f"正解数: {correct_count}/{total_questions}")
        print("=================\n")
        
        # 結果を音声で通知
        self.speak(f"ゲーム終了です。{total_questions}問中{correct_count}問正解でした。")

def normalize_answer(ans):
    # 空白除去・全角半角統一
    ans = ans.replace(" ", "").replace("　", "")
    ans = unicodedata.normalize('NFKC', ans)
    # 数字以外の文字を除去（必要なら）
    return ans

if __name__ == "__main__":
    game = VoiceCalculationGame()
    game.run_game() 