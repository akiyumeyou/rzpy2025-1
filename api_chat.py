#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import subprocess
import speech_recognition as sr
import requests
import json
import sys
import random
import threading
from dotenv import load_dotenv
from conversation_manager import ConversationManager
from typing import Dict, List
import aizuchi  # 相槌機能を外部モジュールから読み込む
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.chains.summarize import load_summarize_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
import whisper
import numpy as np
import sounddevice as sd
import wave
import tempfile

# .envファイルを読み込む
load_dotenv()

# 環境変数からAPIキーを取得
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAIクライアントの初期化
client = OpenAI(api_key=OPENAI_API_KEY)

# LangChainの設定
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.7,
    max_tokens=100,
    api_key=OPENAI_API_KEY
)

# プロンプトテンプレートの設定
prompt = ChatPromptTemplate.from_messages([
    ("system", """あなたは高齢者と会話するアシスタントです。
    以下のルールを守ってください：
    1. 応答は必ず30文字以内にすること
    2. 1文で簡潔に答える
    3. 日常会話で使う自然な話し言葉で話す
    4. 専門用語や難しい言葉は使わない
    5. 「〜ですね」「〜かもしれません」などの曖昧表現は避ける
    6. 質問には直接答える"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])

# 会話チェーンの設定
chain = prompt | llm

# メッセージ履歴の管理
store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

# メッセージ履歴付きのチェーン
conversation = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)

# 要約チェーンの設定
summarize_chain = load_summarize_chain(
    llm,
    chain_type="map_reduce",
    verbose=True
)

# 無言の時間を計測するためのカウンター
silence_counter = 0
MAX_SILENCE = 4  # 最大無言回数（少なくして早めに反応するように）
last_activity_time = time.time()  # 最後の活動時間

# 会話マネージャーのインスタンス
conversation_manager = ConversationManager()

# 短い相槌リスト
SHORT_AIZUCHI = ["うん", "はい", "ええ", "そう"]

# 音声出力中フラグを追加
gpt_speaking = False
speak_queue = []

# TTSエンジンの選択フラグ
USE_OPEN_JTALK = False  # Trueに変更するとOpenJTalkを使用
USE_VOICEVOX = False    # Trueに変更するとVoiceVoxを使用

# 会話履歴の初期化に使う指示を改善
SYSTEM_INSTRUCTION = """あなたは高齢者と会話するアシスタントです。
以下のルールを守ってください：
1. 応答は必ず30文字以内にすること
2. 1文で簡潔に答える
3. 日常会話で使う自然な話し言葉で話す
4. 専門用語や難しい言葉は使わない
5. 「〜ですね」「〜かもしれません」などの曖昧表現は避ける
6. 質問には直接答える
"""

# whisperモデルの初期化（より軽量なモデルを使用）
model = whisper.load_model("tiny")

def speak_with_open_jtalk(text):
    """OpenJTalkを使って音声合成を行う"""
    try:
        # 一時ファイルパス
        temp_dir = "/tmp"
        wav_file = os.path.join(temp_dir, "output.wav")
        
        # OpenJTalkのコマンド
        # 注意: OpenJTalkのインストールが必要です
        # macOSの場合: brew install open-jtalk open-jtalk-utf8
        # 辞書とhtsvoiceのパスは環境に合わせて調整が必要
        cmd = [
            "open_jtalk",
            "-x", "/usr/local/opt/open-jtalk/dic",  # 辞書パス (要確認)
            "-m", "/usr/local/opt/open-jtalk/voice/mei/mei_normal.htsvoice",  # 音声ファイル (要確認)
            "-ow", wav_file,
            "-r", "1.0",   # 速度
            "-fm", "0.0",  # 高さ
            "-a", "0.55",  # ボリューム
            "-jf", "1.0"   # 声の太さ
        ]
        
        # プロセスを実行
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # テキストを送信
        process.stdin.write(text.encode('utf-8'))
        process.stdin.close()
        process.wait()
        
        # 音声を再生
        subprocess.call(["afplay", wav_file])
        
        # 使用後はファイルを削除
        if os.path.exists(wav_file):
            os.remove(wav_file)
            
        return True
    except Exception as e:
        print(f"OpenJTalk エラー: {e}")
        return False

def speak_with_voicevox(text):
    """VoiceVoxを使って音声合成を行う"""
    try:
        # VoiceVoxのAPIエンドポイント (デフォルトポート: 50021)
        # 注意: VoiceVoxアプリを起動しておく必要があります
        # https://voicevox.hiroshiba.jp/ からダウンロード可能
        base_url = "http://localhost:50021"
        
        # 音声合成クエリの作成 (話者ID: 1=ずんだもん ノーマル)
        speaker_id = 1
        
        # 音声パラメータ
        params = {
            "text": text,
            "speaker": speaker_id
        }
        
        # 音声合成クエリを作成
        query_response = requests.post(
            f"{base_url}/audio_query",
            params=params
        )
        
        if query_response.status_code != 200:
            print(f"VoiceVox クエリエラー: {query_response.status_code}")
            return False
        
        query_data = query_response.json()
        
        # 音声合成を実行
        synthesis_response = requests.post(
            f"{base_url}/synthesis",
            headers={"Content-Type": "application/json"},
            params={"speaker": speaker_id},
            data=json.dumps(query_data)
        )
        
        if synthesis_response.status_code != 200:
            print(f"VoiceVox 合成エラー: {synthesis_response.status_code}")
            return False
        
        # 一時ファイルに音声データを保存
        temp_dir = "/tmp"
        wav_file = os.path.join(temp_dir, "voicevox_output.wav")
        
        with open(wav_file, "wb") as f:
            f.write(synthesis_response.content)
        
        # 音声を再生
        subprocess.call(["afplay", wav_file])
        
        # 使用後はファイルを削除
        if os.path.exists(wav_file):
            os.remove(wav_file)
            
        return True
    except Exception as e:
        print(f"VoiceVox エラー: {e}")
        return False

def speak(text, wait=True):
    """テキストを音声で読み上げる"""
    # AIからの応答として表示
    print(f"アシスタント: {text}")
    
    # 会話を記録
    conversation_manager.add_to_conversation("assistant", text)
    
    # 発話中フラグを設定
    global gpt_speaking
    gpt_speaking = True
    
    # TTSエンジンの選択
    tts_success = False
    
    if USE_OPEN_JTALK:
        # OpenJTalkを使用
        tts_success = speak_with_open_jtalk(text)
    elif USE_VOICEVOX:
        # VoiceVoxを使用
        tts_success = speak_with_voicevox(text)
    
    # 失敗した場合やフラグが立っていない場合は標準のsayコマンドを使用
    if not tts_success:
        # 「は」を「わ」と発音させるための置換
        speaking_text = text.replace("は", "わ").replace("初めましょう", "はじめましょう")
        
        # 日本語文章をより自然に読み上げるための処理
        # 句読点で区切って発話をより自然にする
        for mark in ["。", "、", "！", "？"]:
            speaking_text = speaking_text.replace(mark, mark + " ")
        
        # 長い文章を適切に区切る
        if len(speaking_text) > 50:
            # 長い文章は適度に息継ぎを入れる
            parts = speaking_text.split("。")
            speaking_text = "。[[slnc 300]] ".join([p for p in parts if p])
        
        # 強調表現
        if "！" in speaking_text:
            speaking_text = speaking_text.replace("！", "[[emph +]] ！ [[emph 0]]")
        
        # 疑問表現
        if "？" in speaking_text:
            speaking_text = speaking_text.replace("？", "[[inpt PHON]]? [[inpt TEXT]]")
        
        # macOSのsayコマンドを使用（自然な発話のために速度とピッチを調整）
        if wait:
            subprocess.run(["say", "-v", "Kyoko", "-r", "170", speaking_text])
        else:
            # 待たずに次の処理に進む
            process = subprocess.Popen(["say", "-v", "Kyoko", "-r", "170", speaking_text])
            # 非同期で終了を検知
            def monitor_process():
                process.wait()
                global gpt_speaking
                gpt_speaking = False
            threading.Thread(target=monitor_process, daemon=True).start()
    
    # 同期処理の場合は、発話終了後にフラグを戻す
    if wait:
        gpt_speaking = False
    
    # 最後の活動時間を更新
    global last_activity_time
    last_activity_time = time.time()

def say_system_message(message, wait=True):
    """システムメッセージを発話する（相槌など）"""
    global gpt_speaking
    
    # 既に発話中の場合は短い相槌のみキューに追加し、それ以外は無視
    if gpt_speaking:
        if len(message) < 10 and message not in speak_queue:
            speak_queue.append(message)
        return
    
    try:
        gpt_speaking = True
        # 会話を記録
        conversation_manager.add_to_conversation("assistant", message)
        
        # 「は」を「わ」と発音させるための置換
        speaking_text = message.replace("は", "わ").replace("初めましょう", "はじめましょう")
        
        # 日本語文章をより自然に読み上げるための処理
        # 句読点で区切って発話をより自然にする
        for mark in ["。", "、", "！", "？"]:
            speaking_text = speaking_text.replace(mark, mark + " ")
        
        # 長い文章を適切に区切る
        if len(speaking_text) > 30:
            parts = speaking_text.split("。")
            speaking_text = "。[[slnc 250]] ".join([p for p in parts if p])
        
        # AIからの応答として表示
        print(f"アシスタント: {message}")
        
        # macOSのsayコマンドを使用（速度を調整）
        if wait:
            subprocess.run(["say", "-v", "Kyoko", "-r", "170", speaking_text])
        else:
            # 待たずに次の処理に進む
            process = subprocess.Popen(["say", "-v", "Kyoko", "-r", "170", speaking_text])
            # 非同期で終了を検知
            def monitor_process():
                process.wait()
                global gpt_speaking
                gpt_speaking = False
            threading.Thread(target=monitor_process, daemon=True).start()
        
        if wait:
            gpt_speaking = False
        
        # キューに溜まったメッセージがあれば順次発話
        if speak_queue and not wait:
            next_message = speak_queue.pop(0)
            threading.Thread(target=say_system_message, args=(next_message, False), daemon=True).start()
    except Exception as e:
        print(f"システムメッセージ発話中にエラーが発生しました: {e}")
        gpt_speaking = False

def detect_emotion(text: str) -> str:
    """テキストから感情を検出する（後方互換性のために残す）"""
    for emotion, keywords in aizuchi.EMOTION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return emotion
    return "interest"  # デフォルトは「興味」を返す

def say_aizuchi(text):
    """ユーザーの発話内容に基づいて適切な相槌を選んで発話する"""
    global gpt_speaking
    
    # AIが話している間は相槌を出さない
    if gpt_speaking:
        return
        
    try:
        # aizuchi.pyの関数を使用して感情に応じた相槌を選択
        aizuchi_text = aizuchi.select_local_aizuchi(text)
        
        # 相槌を発話する（このときspeak関数内でgpt_speaking = Trueとなることに注意）
        say_system_message(aizuchi_text, wait=False)
    except Exception as e:
        print(f"相槌処理中にエラーが発生しました: {e}")
        # エラー時はデフォルト相槌
        try:
            say_system_message(random.choice(SHORT_AIZUCHI), wait=False)
        except:
            pass

def audio_detection_thread(recognizer, source, result_callback):
    """バックグラウンドで音声を検出するスレッド"""
    try:
        # 音声検出の感度パラメータ調整 - より敏感に反応するように値を下げる
        recognizer.energy_threshold = 1000  # 以前は1500
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.5  # 以前は0.8、短くして素早く反応
        
        print("音声検出待機中...")
        # タイムアウトを調整して素早く反応
        audio = recognizer.listen(source, timeout=0.5, phrase_time_limit=1.0)  # 以前は1.0と1.5
        
        # 相槌を出すのは確実に音声があるときだけ、かつAIが話していないとき
        if result_callback and not gpt_speaking and audio and len(audio.frame_data) > 2000:
            threading.Thread(
                target=lambda: result_callback(True),
                daemon=True
            ).start()
    except sr.WaitTimeoutError:
        # タイムアウトは正常な状態なのでエラーではない
        pass
    except Exception as e:
        print(f"音声検出スレッドでエラー: {e}")
        # エラー発生時は相槌を抑制
        # if result_callback:
        #     threading.Thread(
        #         target=lambda: result_callback(False),
        #         daemon=True
        #     ).start()

def record_audio(duration=3, sample_rate=16000):
    """音声を録音する"""
    audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype=np.float32)
    sd.wait()
    return audio

def save_audio(audio, sample_rate=16000):
    """録音した音声を一時ファイルに保存"""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        with wave.open(temp_file.name, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes((audio * 32767).astype(np.int16).tobytes())
        return temp_file.name

def listen(conversation_history=None):
    """音声を認識して返す"""
    try:
        # 3秒間の音声を録音
        audio = record_audio(duration=3)
        
        # 一時ファイルに保存
        temp_file = save_audio(audio)
        
        # whisperで音声認識（オプションを追加して高速化）
        result = model.transcribe(
            temp_file,
            language="ja",
            task="transcribe",
            fp16=False,
            verbose=False
        )
        
        # 一時ファイルを削除
        os.unlink(temp_file)
        
        if result["text"].strip():
            return result["text"].lower()
        else:
            return None
            
    except Exception as e:
        print(f"音声認識エラー: {e}")
        return None

def create_summary():
    """会話の要約を作成"""
    try:
        # 現在のセッションの会話履歴を取得
        session_id = "default_session"
        history = get_session_history(session_id)
        
        if not history.messages:
            return "まだ十分な会話がありません。"
        
        # 会話履歴をテキストに変換
        conversation_text = "\n".join([
            f"{msg.type}: {msg.content}" for msg in history.messages
        ])
        
        # テキストを分割
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        texts = text_splitter.split_text(conversation_text)
        docs = [Document(page_content=t) for t in texts]
        
        # 要約を生成
        summary = summarize_chain.run(docs)
        return summary
    except Exception as e:
        print(f"要約の生成中にエラーが発生しました: {e}")
        return "要約の生成に失敗しました。"

def get_aizuchi(text):
    """ユーザーの発話に応じた相槌を生成"""
    prompt = f"""
    以下のユーザーの発話に対して、自然な相槌を1つだけ返してください。
    相槌は「うん」「はい」「そうですね」「なるほど」などの短い言葉にしてください。
    
    ユーザーの発話: {text}
    """
    
    response = llm.invoke(prompt)
    return response.content.strip()

def suggest_topic():
    """会話履歴に基づいて新しい話題を提案"""
    # 現在のセッションの会話履歴を取得
    session_id = "default_session"
    history = get_session_history(session_id)
    
    # 会話履歴が少ない場合はデフォルトのトピックを返す
    if len(history.messages) < 2:
        default_topics = [
            "今日はどんな一日でしたか？",
            "最近見た映画や読んだ本について教えてください",
            "お気に入りの食べ物は何ですか？",
            "今日のニュースで気になることはありますか？",
            "天気はどうですか？"
        ]
        return random.choice(default_topics)
    
    # 会話履歴からトピックを提案
    prompt = f"""
    以下の会話履歴を参考に、自然な形で新しい話題を提案してください。
    提案は「そういえば、」で始めてください。
    
    会話履歴:
    {history.messages}
    """
    
    response = llm.invoke(prompt)
    return response.content.strip()

def get_conversation_summary():
    """会話の要約を取得"""
    try:
        # 現在のセッションの会話履歴を取得
        session_id = "default_session"
        history = get_session_history(session_id)
        
        if not history.messages:
            return "まだ十分な会話がありません。"
        
        # 会話履歴をテキストに変換
        conversation_text = "\n".join([
            f"{msg.type}: {msg.content}" for msg in history.messages
        ])
        
        # テキストを分割
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        texts = text_splitter.split_text(conversation_text)
        docs = [Document(page_content=t) for t in texts]
        
        # 要約を生成
        summary = summarize_chain.run(docs)
        return summary
    except Exception as e:
        print(f"要約の生成中にエラーが発生しました: {e}")
        return "要約の生成に失敗しました。"

def start_voice_chat():
    """音声チャットを開始"""
    # APIキーの確認
    if not OPENAI_API_KEY:
        print("APIキーが設定されていません。")
        return
    
    print("音声チャットを開始します。")
    print("終了するには「終了」「さようなら」「ありがとう」と言ってください。")
    print("会話の要約を取得するには「要約して」と言ってください。")
    
    # セッションIDの設定
    session_id = "default_session"
    
    # 最初の話題を提供
    initial_topics = [
        "今日はどんな一日でしたか？",
        "最近見た映画や読んだ本について教えてください",
        "お気に入りの食べ物は何ですか？",
        "今日のニュースで気になることはありますか？",
        "天気はどうですか？",
        "何か楽しい予定はありますか？",
        "最近うれしかったことを教えてください",
        "健康のために何か気をつけていることはありますか？",
        "昔の思い出について話しませんか？",
        "今度の休みには何をする予定ですか？"
    ]
    initial_topic = random.choice(initial_topics)
    speak(f"そういえば、{initial_topic}")
    
    try:
        while True:
            # ユーザーの入力を取得
            user_input = listen()
            
            if user_input is None:
                continue
            
            # 終了コマンドの確認
            if any(cmd in user_input for cmd in ["終了", "さようなら", "ありがとう"]):
                speak("さようなら！またお話しましょう。")
                break
            
            # 要約コマンドの確認
            if "要約して" in user_input:
                summary = create_summary()
                speak(summary)
                continue
            
            # 相槌を出す
            aizuchi = get_aizuchi(user_input)
            speak(aizuchi, wait=False)
            
            # 会話を続行
            response = conversation.invoke(
                {"input": user_input},
                config={"configurable": {"session_id": session_id}}
            )
            speak(response.content)
    
    except KeyboardInterrupt:
        print("\n会話を終了します。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        # 会話履歴を保存（非同期で実行）
        def save_summary_async():
            try:
                summary = create_summary()
                with open("conversation_summary.txt", "w", encoding="utf-8") as f:
                    f.write(summary)
            except Exception as e:
                print(f"要約の保存中にエラーが発生しました: {e}")
        
        # 非同期で要約を保存
        threading.Thread(target=save_summary_async, daemon=True).start()

if __name__ == "__main__":
    start_voice_chat() 