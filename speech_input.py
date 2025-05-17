#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import queue
import time
import speech_recognition as sr

# 音声認識の状態管理
is_user_speaking = False

def get_is_user_speaking():
    """ユーザーが話しているかどうかを返す"""
    return is_user_speaking

def listen(vocabulary: list[str] | None = None):
    """音声を認識して返す。vocabularyは無視（SpeechRecognitionでは限定語彙未対応）"""
    global is_user_speaking
    is_user_speaking = True
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("音声認識待機中...")
        r.adjust_for_ambient_noise(source)
        try:
            audio = r.listen(source, timeout=10, phrase_time_limit=5)
            print("認識中...")
            text = r.recognize_google(audio, language='ja-JP')
            print(f"認識結果: {text}")
            is_user_speaking = False
            return text
        except sr.WaitTimeoutError:
            print("音声が検出されませんでした。")
        except sr.UnknownValueError:
            print("認識できた発話がありません。")
        except sr.RequestError as e:
            print(f"音声認識サービスに接続できません: {e}")
        except Exception as e:
            print(f"音声認識中にエラーが発生しました: {e}")
    is_user_speaking = False
    return None

if __name__ == "__main__":
    print("音声認識テストを開始します...")
    result = listen()
    if result:
        print(f"認識結果: {result}")
    else:
        print("音声を認識できませんでした。")