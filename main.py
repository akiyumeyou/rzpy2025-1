#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
from dotenv import load_dotenv
from speech_input import listen
from speech_output import speak
from api_chat import start_voice_chat
from voice_calc_game import VoiceCalculationGame
from file_operations import save_conversation_record
import subprocess
import webbrowser  # ← 追加

# .envファイルの読み込み
load_dotenv()

def main():
    """メインプログラム"""
    try:
        # 初期化
        print("システムを起動しています...")
        speak("もしもし。おしゃべり、脳トレゲーム、ポッツに接続のどれをしますか？")
        
        while True:
            # モード選択
            user_input = listen()
            if user_input is None:
                continue
                
            # 「終了」や「さようなら」「終わります」で終了
            if any(word in user_input for word in ["終了", "さようなら", "終わります", "終了します"]):
                speak("プログラムを終了します。")
                break
                
            # モード判定
            normalized_input = user_input.replace(" ", "").replace("　", "")
            if "おしゃべり" in normalized_input:
                speak("おしゃべりしましょう")
                start_voice_chat()
                speak("おしゃべりを終了しました。次は何かしますか？おしゃべり、脳トレゲーム、ポッツに接続、または終了しますか？")
                continue
                
            elif "脳トレ" in user_input or "ゲーム" in user_input:
                speak("脳トレゲームをしましょう")
                game = VoiceCalculationGame()
                game.run_game()
                speak("脳トレゲームを終了しました。次は何かしますか？おしゃべり、脳トレゲーム、ポッツに接続、または終了しますか？")
                continue
                
            elif "ポッツ" in user_input or "接続" in user_input:
                speak("ポッツへの接続を開始します")
                webbrowser.open("https://ftc.potz.jp/dashboard")
                time.sleep(3)
                speak("ポッツに接続しました。次は何かしますか？おしゃべり、脳トレゲーム、ポッツに接続、または終了しますか？")
                continue
                
            else:
                speak("選んでください")
                print("選択可能なモード：")
                print("1. おしゃべり")
                print("2. 脳トレゲーム")
                print("3. ポッツに接続")
                print("4. 終了します")
                
    except KeyboardInterrupt:
        print("\nプログラムを終了します")
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()