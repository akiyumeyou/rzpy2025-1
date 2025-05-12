#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess

def speak(text):
    """テキストを音声で読み上げる"""
    print(f"コンピュータ: {text}")
    
    # OSの判定
    if sys.platform == 'darwin':  # Macの場合
        subprocess.run(['say', '-v', 'Kyoko', text])
    else:  # Raspberry Piの場合
        wav_path = "/tmp/openjtalk.wav"
        dic_path = "/var/lib/mecab/dic/open-jtalk/naist-jdic"
        voice_path = "/usr/share/hts-voice/nitech-jp-atr503-m001/nitech_jp_atr503_m001.htsvoice"
        
        # Open JTalkのコマンドを構築
        cmd = [
            "open_jtalk",
            "-x", dic_path,
            "-m", voice_path,
            "-r", "1.5",
            "-ow", wav_path
        ]
        
        # テキストを音声に変換
        subprocess.run(f'echo "{text}" | ' + ' '.join(cmd), shell=True)
        
        # 音声を再生
        subprocess.run(["aplay", wav_path])
