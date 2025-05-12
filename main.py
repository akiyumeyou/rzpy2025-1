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

# .envファイルの読み込み
load_dotenv()

def main():
    """メインプログラム"""
    try:
        # 初期化
        print("システムを起動しています...")
        speak("こんにちは。おしゃべり、脳トレゲーム、ポッツに接続のどれをしますか？")
        
        while True:
            # モード選択
            user_input = listen()
            if user_input is None:
                continue
                
            # モード判定
            normalized_input = user_input.replace(" ", "").replace("　", "")
            if "おしゃべり" in normalized_input:
                speak("おしゃべりを開始します")
                start_voice_chat()
                break
                
            elif "脳トレ" in user_input or "ゲーム" in user_input:
                speak("脳トレゲームを開始します")
                game = VoiceCalculationGame()
                game.run_game()
                break
                
            elif "ポッツ" in user_input or "接続" in user_input:
                speak("ポッツへの接続を開始します")
                # TODO: ポッツ接続機能の実装
                speak("申し訳ありません。この機能は現在開発中です")
                break
                
            else:
                speak("すみません、もう一度お選びください")
                print("選択可能なモード：")
                print("1. おしゃべり")
                print("2. 脳トレゲーム")
                print("3. ポッツに接続")
                
    except KeyboardInterrupt:
        print("\nプログラムを終了します")
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()