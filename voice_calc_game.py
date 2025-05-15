#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import speech_recognition as sr
import subprocess
import time
from conversation_manager import ConversationManager
from speech_output import speak
from datetime import datetime
from file_operations import save_calc_game_result


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
        # 「は？」を「wa?」に置換（出題文用）
        speaking_text = text.replace("は？", "わ？").replace("は", "わ").replace("初めましょう", "はじめましょう")
        subprocess.run(["say", "-v", "Kyoko", speaking_text])
    
    def listen(self):
        """音声を認識して返す（短い発話を素早くキャッチ）"""
        with self.microphone as source:
            print("聞いています...")
            try:
                audio = self.recognizer.listen(source, timeout=5.0, phrase_time_limit=2.0)
                text = self.recognizer.recognize_google(audio, language='ja-JP')
                print(f"認識された発話: {text}")
                self.conversation_manager.add_to_conversation("user", text)
                return text.lower()
            except sr.WaitTimeoutError:
                speak("声が聞こえませんでした。もう一度お願いします。")
                return None
            except sr.UnknownValueError:
                speak("すみません、聞き取れませんでした。もう一度お願いします。")
                return None
            except sr.RequestError:
                speak("音声認識サービスに接続できませんでした。ネットワーク接続を確認してください。")
                return None
    
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
            question = f"{a}たす{b}わ？"
        elif operator == "-":
            answer = a - b
            question = f"{a}ひく{b}わ？"
        elif operator == "*":
            answer = a * b
            question = f"{a}かける{b}わ？"
        else:  # "/"
            question = f"{a}わる{b}わ？"
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
            
            response = self.listen()
            if response is None:
                # もう一度同じ問題を出します。
                speak("もう一度同じ問題を出します。")
                speak(question)
                response = self.listen()
                if response is None:
                    detail_results.append(f"{i}問目: スキップ")
                    continue
            
            if "終了" in response:
                detail_results.append(f"{i}問目: ユーザーが終了を選択")
                break
            
            try:
                user_answer = int(response)
                if user_answer == answer:
                    speak("正解です！")
                    score += 1
                    detail_results.append(f"{i}問目: 正解")
                else:
                    speak(f"残念、正解は{answer}でした。")
                    detail_results.append(f"{i}問目: 不正解（答: {answer}）")
            except ValueError:
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