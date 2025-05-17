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
from speech_output import speak
from speech_input import listen, get_is_user_speaking
import openai
from file_operations import save_conversation_record, save_conversation_summary
import asyncio
import aizuchi  # aizuchi.py をインポート

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
    ("system", "あなたは高齢者と会話する優しい人です。やさしい日本語で短く返してください。"),
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

def load_topics():
    try:
        with open(os.path.join(os.path.dirname(__file__), 'conversation_history', 'topics.json'), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"話題リストの読み込みに失敗: {e}")
        return []

TOPIC_STOCK = load_topics()


def detect_intent_with_aizuchi(user_input: str):
    # aizuchi.pyのキーワードを活用
    detected = []
    for emotion, keywords in aizuchi.EMOTION_KEYWORDS.items():
        if any(keyword in user_input for keyword in keywords):
            detected.append(emotion)
    if detected:
        return detected[0]  # 最初の意図を返す
    # 質問形
    if user_input.endswith("？") or user_input.endswith("?") or "とは" in user_input or "教えて" in user_input:
        return "question"
    # 話題要求
    if any(word in user_input for word in ["話題", "何か話", "面白い話", "提案", "おすすめ", "困った", "沈黙"]):
        return "request_topic"
    # 短い発話
    if len(user_input.strip()) <= 2:
        return "short"
    return "chat"


def suggest_topic_from_stock():
    if TOPIC_STOCK:
        return random.choice(TOPIC_STOCK)
    # デフォルト
    return "最近気になることはありますか？"


def generate_response(user_input, history):
    """ユーザーの入力に応じて応答を生成（意図判定・話題ストック・LLM活用）"""
    try:
        messages = history.get_messages()
        session_id = "default_session"
        intent = detect_intent_with_aizuchi(user_input)
        last_message = messages[-1] if messages else None
        last_is_aizuchi = last_message and last_message.get('role') == 'assistant' and \
            any(word in last_message.get('content', '') for word in ["はい", "ええ", "そうですね"] + aizuchi.DEFAULT_RESPONSES)

        # 1. 話題要求
        if intent == "request_topic":
            return suggest_topic_from_stock()

        # 2. 質問
        if intent == "question":
            prompt = f"ユーザーからの質問に、やさしい日本語で50文字以内、2文以内で短く丁寧に答えてください。\n質問: {user_input}"
            response = llm.invoke(prompt)
            return response.content.strip()

        # 3. 感情・興味
        if intent in ["happy", "sad", "interest"]:
            aizuchi_resp = aizuchi.select_local_aizuchi(user_input)
            # 共感のみ、または共感＋一言
            return f"{aizuchi_resp}"

        # 4. 短い発話
        if intent == "short":
            if last_is_aizuchi:
                return suggest_topic_from_stock()
            return random.choice([r for r in ["はい", "ええ", "そうですね"] if r != (last_message.get('content') if last_message else None)])

        # 5. 通常の雑談
        prompt = f"高齢者と会話しています。やさしい日本語で、共感しながら50文字以内、2文以内で短く返してください。\nユーザー: {user_input}\n"
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        print(f"応答生成エラー: {e}")
        return "すみません、もう一度お願いします。"

def save_conversation_background(history):
    thread = threading.Thread(target=save_conversation_record, args=(history,))
    thread.start()

def postprocess_response(response: str) -> str:
    # 先頭のAI:やアシスタント:などを除去
    for prefix in ["AI:", "アシスタント:", "Assistant:", "assistant:", "ＡＩ："]:
        if response.startswith(prefix):
            response = response[len(prefix):].strip()
    return response

def start_voice_chat():
    """音声対話を開始"""
    print("音声対話を開始します。終了するには「終了」と言ってください。")
    
    # 会話履歴の初期化
    history = ConversationHistory()
    start_time = time.time()
    
    # 初期トピックの提案
    initial_topics = [
        "今日はどのようにお過ごしですか？",
        "楽しかったことはありました？",
        "何のお話が良いですか？"
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
            response = postprocess_response(response)
            speak(response)
            history.add_message("assistant", response)

if __name__ == "__main__":
    start_voice_chat()