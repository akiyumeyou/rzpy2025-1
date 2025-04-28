#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import speech_recognition as sr
import subprocess
import time
from conversation_manager import ConversationManager

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
        self.speak("脳トレゲームを始めます。計算問題を出しますので、答えを言ってください。")
        self.speak("ゲームを終了するには、「終了」と言ってください。")
        
        score = 0
        total_questions = 0
        
        while True:
            question, answer = self.generate_question()
            self.speak(question)
            
            response = self.listen()
            if response is None:
                continue
                
            if "終了" in response:
                break
                
            try:
                user_answer = int(response)
                total_questions += 1
                
                if user_answer == answer:
                    self.speak("正解です！")
                    score += 1
                else:
                    self.speak(f"残念、正解は{answer}でした。")
                
                # スコアを表示
                self.speak(f"現在のスコアは{score}問正解、{total_questions}問中です。")
                
            except ValueError:
                self.speak("数字で答えてください。")
        
        # 最終結果を表示
        self.speak(f"ゲーム終了です。{total_questions}問中{score}問正解でした。")
        self.speak("お疲れ様でした。")

if __name__ == "__main__":
    game = VoiceCalculationGame()
    game.run_game() 