#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import numpy as np
import time

# 音声認識の設定
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 8000

# 音声認識の状態管理
is_user_speaking = False
audio_queue = queue.Queue()

# Voskモデルの初期化（一度だけ）
model_path = os.path.join(os.path.dirname(__file__), "model")
if not os.path.exists(model_path):
    raise Exception(f"Voskモデルが見つかりません: {model_path}")
model = Model(model_path)
recognizer = KaldiRecognizer(model, SAMPLE_RATE)
recognizer.SetWords(True)

def get_is_user_speaking():
    """ユーザーが話しているかどうかを返す"""
    return is_user_speaking

def audio_callback(indata, frames, time, status):
    """音声入力のコールバック関数"""
    if status:
        print(status)
    audio_queue.put(bytes(indata))

def listen():
    """音声を認識して返す"""
    global is_user_speaking
    is_user_speaking = True
    
    try:
        sample_rate = 16000
        channels = 1
        silence_threshold = 1.5  # 沈黙の閾値を1.5秒に短縮
        min_speech_duration = 0.3  # 最小発話時間を0.3秒に設定
        max_wait_time = 10  # 最大待機時間を10秒に短縮
        consecutive_silence_threshold = 3  # 連続沈黙の閾値
        
        with sd.RawInputStream(samplerate=sample_rate, blocksize=8000,
                             device=None, dtype='int16',
                             channels=channels, callback=audio_callback):
            print("音声認識待機中...")
            
            start_time = time.time()
            last_speech_time = time.time()
            full_text = []
            is_complete = False
            speech_started = False
            consecutive_silence = 0
            last_text = ""
            
            while not is_complete:
                try:
                    data = audio_queue.get(timeout=0.5)  # タイムアウトを0.5秒に短縮
                except queue.Empty:
                    if time.time() - start_time > max_wait_time:
                        print("音声が検出されませんでした。")
                        break
                    continue
                    
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").strip()
                    
                    if text:
                        if not speech_started:
                            speech_started = True
                            print("音声を検出しました...")
                            consecutive_silence = 0
                        
                        # 前回と同じテキストが連続して出てきた場合は無視
                        if text != last_text:
                            print(f"認識結果: {text}")
                            full_text.append(text)
                            last_text = text
                            last_speech_time = time.time()
                            consecutive_silence = 0
                    else:
                        consecutive_silence += 1
                
                # 沈黙が続く場合に区切りと判断
                if speech_started and (time.time() - last_speech_time > silence_threshold or consecutive_silence >= consecutive_silence_threshold):
                    final_result = json.loads(recognizer.FinalResult())
                    final_text = final_result.get("text", "").strip()
                    
                    if final_text and final_text != last_text:
                        print(f"最終認識結果: {final_text}")
                        full_text.append(final_text)
                    
                    if time.time() - start_time >= min_speech_duration:
                        is_complete = True
                    else:
                        print("発話時間が短すぎます。もう一度お願いします。")
                        speech_started = False
                        start_time = time.time()
                        last_speech_time = time.time()
                        full_text = []
                        consecutive_silence = 0
                        last_text = ""
                
                if time.time() - start_time > max_wait_time:
                    if not speech_started:
                        print("音声が検出されませんでした。")
                    break
            
            is_user_speaking = False
            if full_text:
                combined_text = " ".join(full_text)
                combined_text = " ".join(combined_text.split())
                combined_text = combined_text.rstrip("、。,.!?")
                print(f"最終認識結果: {combined_text}")
                return combined_text
            print("認識できた発話がありません。")
            return None
            
    except Exception as e:
        print(f"音声認識中にエラーが発生しました: {e}")
        is_user_speaking = False
        return None

if __name__ == "__main__":
    # テスト用のコード
    print("音声認識テストを開始します...")
    result = listen()
    if result:
        print(f"認識結果: {result}")
    else:
        print("音声を認識できませんでした。")