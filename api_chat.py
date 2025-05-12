#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import subprocess
import requests
import json
import sys
import random
import threading
from datetime import datetime
from dotenv import load_dotenv
from conversation_manager import ConversationManager
from typing import Dict, List
from aizuchi import select_local_aizuchi
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
import numpy as np
import sounddevice as sd
import wave
import tempfile
import queue
from vosk import Model, KaldiRecognizer
from speech_output import speak
from speech_input import listen, get_is_user_speaking
import openai
from file_operations import save_conversation_record, save_conversation_summary
import asyncio

# .envファイル読み込み
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAIクライアント
client = OpenAI(api_key=OPENAI_API_KEY)

# LangChain設定
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.7,
    max_tokens=100,
    api_key=OPENAI_API_KEY
)

prompt = ChatPromptTemplate.from_messages([
    ("system", """あなたは高齢者と会話するアシスタントです。
以下のルールを厳密に守ってください：

1. ユーザーの発言が短い場合（3文字以下）は、相槌のみを返す。
2. ユーザーの発言が不明確な場合は、具体的な質問をせず、相槌のみを返す。
3. ユーザーが明示的に話題を変えるまで、現在の話題を維持する。
4. 勝手に話題を展開しない。
5. 相槌は「はい」「ええ」「そうですね」のみを使用し、1回だけ返す。
6. ユーザーが「話したくない」と示した場合は、話題を変えずに相槌のみを返す。
7. ユーザーの発言が文章として不完全な場合は、相槌のみを返す。
8. 会話の主導権は常にユーザーに委ねる。

現在の会話の文脈：
{chat_history}"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])

chain = prompt | llm
store = {}

# 会話マネージャーのインスタンス
conversation_manager = ConversationManager()

class ConversationHistory:
    def __init__(self):
        self.messages = []
    
    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})
    
    def get_messages(self):
        return self.messages

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

conversation = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)

# 音声認識の設定
audio_queue = queue.Queue()
model_path = os.path.join(os.path.dirname(__file__), "model")
vosk_model = Model(model_path)
recognizer = KaldiRecognizer(vosk_model, 16000)
recognizer.SetWords(True)

def audio_callback(indata, frames, time, status):
    """音声入力のコールバック関数"""
    if status:
        print(status)
    audio_queue.put(bytes(indata))

# 沈黙検知の設定
SILENCE_THRESHOLD = 20  # 20秒
last_activity_time = time.time()

def get_is_user_speaking():
    return is_user_speaking

def listen():
    """音声を認識して返す"""
    global is_user_speaking
    is_user_speaking = True
    
    try:
        sample_rate = 16000
        channels = 1
        silence_threshold = 2.0  # 沈黙の閾値を2秒に延長
        
        with sd.RawInputStream(samplerate=sample_rate, blocksize=8000,
                             device=None, dtype='int16',
                             channels=channels, callback=audio_callback):
            print("音声認識待機中...")
            
            # 音声認識の開始
            start_time = time.time()
            last_speech_time = time.time()
            full_text = []
            is_complete = False
            
            while not is_complete:
                data = audio_queue.get()
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "")
                    if text:
                        print(f"認識結果: {text}")
                        full_text.append(text)
                        last_speech_time = time.time()
                
                # 沈黙が続く場合に区切りと判断
                if time.time() - last_speech_time > silence_threshold:
                    # 最後の認識結果を確認
                    final_result = json.loads(recognizer.FinalResult())
                    final_text = final_result.get("text", "")
                    if final_text:
                        full_text.append(final_text)
                    is_complete = True
                
                # 最大15秒まで待機
                if time.time() - start_time > 15:
                    break
            
            is_user_speaking = False
            return " ".join(full_text) if full_text else None
            
    except Exception as e:
        print(f"音声認識中にエラーが発生しました: {e}")
        is_user_speaking = False
        return None

def create_summary():
    session_id = "default_session"
    history = get_session_history(session_id)
    if not history.messages:
        return "まだ十分な会話がありません。"
    conversation_text = "\n".join([f"{msg.type}: {msg.content}" for msg in history.messages])
    texts = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_text(conversation_text)
    docs = [Document(page_content=t) for t in texts]
    summary = summarize_chain.run(docs)
    return summary

def create_family_message():
    """家族向けのメッセージを作成（60文字以内）"""
    try:
        session_id = "default_session"
        history = get_session_history(session_id)
        
        if not history.messages:
            return "今日は会話がありませんでした。"
        
        # 会話履歴をテキストに変換
        conversation_text = "\n".join([
            f"{msg.type}: {msg.content}" for msg in history.messages
        ])
        
        # 家族向けメッセージのプロンプト
        family_prompt = f"""
        以下の会話内容から、家族向けにメッセージを60文字以内で作成してください。
        １、感情表現や家族へのメッセージがあれば優先的に含める。
        ２、日本語で、温かみのある表現。
        ３、どんな会話をしていたのかを明確にする。
        
        会話内容:
        {conversation_text}
        """
        
        response = llm.invoke(family_prompt)
        return response.content.strip()
    except Exception as e:
        print(f"家族向けメッセージの生成中にエラーが発生しました: {e}")
        return "メッセージの生成に失敗しました。"

def suggest_topic():
    """会話履歴から新しい話題を提案"""
    try:
        session_id = "default_session"
        history = get_session_history(session_id)
        
        if len(history.messages) < 2:
            default_topics = [
                "今日はどんな一日でしたか？",
                "最近見た映画や読んだ本について教えてください",
                "お気に入りの食べ物は何ですか？",
                "今日のニュースで気になることはありますか？",
                "天気はどうですか？"
            ]
            return random.choice(default_topics)
        
        # 会話履歴から話題を提案
        topic_prompt = f"""
        以下の会話履歴を参考に、自然な形で新しい話題を提案してください。
        提案は「そういえば、」で始めてください。
        日本語で、会話の流れを考慮した話題を提案してください。
        
        会話履歴:
        {history.messages}
        """
        
        response = llm.invoke(topic_prompt)
        return response.content.strip()
    except Exception as e:
        print(f"話題提案中にエラーが発生しました: {e}")
        return "話題の提案に失敗しました。"

def generate_response(user_input, history):
    """ユーザーの入力に応じて応答を生成"""
    try:
        # 会話履歴を取得
        messages = history.get_messages()
        
        # セッションIDを設定
        session_id = "default_session"
        
        # 短い発話の場合は相槌のみを返す
        if len(user_input) <= 3:
            return random.choice(["はい", "ええ", "そうですね"])
        
        # 文脈を考慮した応答生成
        if len(messages) > 0:
            last_message = messages[-1]
            if last_message.get('role') == 'assistant':
                # 前回の応答が相槌だった場合、次の応答は相槌を避ける
                if any(word in last_message.get('content', '') for word in ["はい", "ええ", "そうですね"]):
                    # より具体的な応答を生成
                    response = conversation.invoke(
                        {
                            "input": user_input,
                            "chat_history": messages[:-1]  # 最後の相槌を除いた履歴を使用
                        },
                        {"configurable": {"session_id": session_id}}
                    )
                else:
                    # 通常の応答生成
                    response = conversation.invoke(
                        {
                            "input": user_input,
                            "chat_history": messages
                        },
                        {"configurable": {"session_id": session_id}}
                    )
            else:
                # 通常の応答生成
                response = conversation.invoke(
                    {
                        "input": user_input,
                        "chat_history": messages
                    },
                    {"configurable": {"session_id": session_id}}
                )
        else:
            # 初回の応答生成
            response = conversation.invoke(
                {
                    "input": user_input,
                    "chat_history": []
                },
                {"configurable": {"session_id": session_id}}
            )
        
        return response.content if hasattr(response, 'content') else str(response)
    except Exception as e:
        print(f"応答生成エラー: {e}")
        return "すみません、もう一度お願いします。"

def save_conversation_background(history):
    thread = threading.Thread(target=save_conversation_record, args=(history,))
    thread.start()

def start_voice_chat():
    """音声対話を開始"""
    print("音声対話を開始します。終了するには「終了」と言ってください。")
    
    # 会話履歴の初期化
    history = ConversationHistory()
    start_time = time.time()
    
    # 初期トピックの提案
    initial_topics = [
        "今日の天気はどうですか？",
        "最近、楽しかったことはありますか？",
        "お気に入りの食べ物は何ですか？"
    ]
    initial_topic = random.choice(initial_topics)
    speak(initial_topic)
    
    while True:
        user_input = listen()
        if not user_input:
            continue
            
        print(f"ユーザー: {user_input}")  # ユーザーの発話を表示
        
        if "終了" in user_input:
            end_time = time.time()
            speak("会話を終了します。")
            # 会話履歴の保存
            try:
                save_conversation_summary(history.get_messages(), start_time, end_time)
            except Exception as e:
                print(f"会話履歴の保存に失敗しました: {e}")
            break
            
        history.add_message("user", user_input)
        response = generate_response(user_input, history)
        
        if response:  # 応答がある場合のみ話す
            speak(response)
            history.add_message("assistant", response)

if __name__ == "__main__":
    start_voice_chat()