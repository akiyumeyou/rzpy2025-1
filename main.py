#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import speech_recognition as sr
import webbrowser
import time
import sys
from voice_calc_game import VoiceCalculationGame
import api_chat
from conversation_manager import ConversationManager

# 会話マネージャーのインスタンス
conversation_manager = ConversationManager()

def speak(text):
    """テキストを音声で読み上げる"""
    print(f"コンピュータ: {text}")
    # 会話を記録
    conversation_manager.add_to_conversation("system", text)
    # 「は」を「わ」と発音させるための置換
    speaking_text = text.replace("は", "わ").replace("初めましょう", "はじめましょう")
    # macOSのsayコマンドを使用
    subprocess.run(["say", "-v", "Kyoko", speaking_text])

def listen():
    """音声を認識して返す"""
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    with microphone as source:
        speak("どうぞ、")
        print("聞いています...")
        try:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source, timeout=10.0)
            text = recognizer.recognize_google(audio, language='ja-JP')
            print(f"認識された発話: {text}")
            # 会話を記録
            conversation_manager.add_to_conversation("user", text)
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

def display_summary():
    """セッションの要約を表示"""
    summary = conversation_manager.get_summary()
    print("\n=== セッションの要約 ===")
    print(summary)
    print("=====================\n")

def main():
    """メイン処理"""
    speak("もしもし。今の私は、おしゃべり、脳トレゲーム、ポッツ接続ができます。選んでください")
    
    while True:
        command = listen()
        if command is None:
            continue
            
        if "おしゃべり" in command:
            speak("おしゃべりを始めます")
            api_chat.start_voice_chat()
            speak("メニューに戻りました。次は何をしますか？")
            
        elif "脳トレ" in command:
            speak("脳トレゲームを始めます")
            game = VoiceCalculationGame()
            game.run_game()
            speak("メニューに戻りました。次は何をしますか？")
            
        elif "ポッツ" in command or "接続" in command:
            speak("ポッツに接続します")
            webbrowser.open("https://ftc.potz.jp/dashboard")
            time.sleep(3)
            speak("ポッツに接続しました。メニューから選んでください")
            
        elif "終了" in command or "さようなら" in command:
            speak("プログラムを終了します。")
            display_summary()
            sys.exit(0)

if __name__ == "__main__":
    main() 