#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import csv
import random
import datetime
from collections import defaultdict

class ConversationManager:
    def __init__(self, storage_dir="conversation_history"):
        """会話履歴管理クラスの初期化"""
        self.storage_dir = storage_dir
        self.current_conversation = []
        self.topics = []
        self.game_results = []
        self.summaries = []
        
        # 保存ディレクトリの作成
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # 過去の会話トピックと要約の読み込み
        self.load_topics()
        self.load_summaries()
    
    def load_topics(self):
        """過去の会話トピックを読み込む"""
        topics_file = os.path.join(self.storage_dir, "topics.json")
        if os.path.exists(topics_file):
            try:
                with open(topics_file, "r", encoding="utf-8") as f:
                    self.topics = json.load(f)
            except Exception as e:
                print(f"トピック読み込みエラー: {e}")
                self.topics = []
        else:
            # デフォルトのトピック
            self.topics = [
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
            self.save_topics()
    
    def load_summaries(self):
        """過去の会話要約を読み込む"""
        summaries_file = os.path.join(self.storage_dir, "summaries.json")
        if os.path.exists(summaries_file):
            try:
                with open(summaries_file, "r", encoding="utf-8") as f:
                    self.summaries = json.load(f)
            except Exception as e:
                print(f"要約読み込みエラー: {e}")
                self.summaries = []
    
    def save_topics(self):
        """トピックをファイルに保存"""
        topics_file = os.path.join(self.storage_dir, "topics.json")
        try:
            with open(topics_file, "w", encoding="utf-8") as f:
                json.dump(self.topics, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"トピック保存エラー: {e}")
    
    def save_summaries(self):
        """要約をファイルに保存"""
        summaries_file = os.path.join(self.storage_dir, "summaries.json")
        try:
            with open(summaries_file, "w", encoding="utf-8") as f:
                json.dump(self.summaries, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"要約保存エラー: {e}")
    
    def add_summary(self, summary_text):
        """会話要約を追加"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.summaries.append({
            "timestamp": timestamp,
            "text": summary_text
        })
        # 要約は最大100件まで保存
        if len(self.summaries) > 100:
            self.summaries = self.summaries[-100:]
        self.save_summaries()
    
    def add_to_conversation(self, speaker, text):
        """会話を記録"""
        # プログラム終了コマンドは記録しない
        if speaker == "user" and ("プログラム終了" in text or "プログラムを終了" in text):
            return
            
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.current_conversation.append({
            "timestamp": timestamp,
            "speaker": speaker,
            "text": text
        })
        
        # ユーザーの発言から新しいトピックを抽出
        if speaker == "user" and len(text) > 5:
            # 短い応答や相槌はスキップ
            if not any(word in text for word in ["うん", "はい", "そうですね", "なるほど"]):
                # 質問でない場合は会話トピックとして記録
                if "？" not in text and "?" not in text:
                    # 重複を避けてトピックを追加
                    if text not in self.topics and len(self.topics) < 100:  # 最大100トピックまで
                        self.topics.append(text)
                        self.save_topics()
    
    def get_random_topic(self):
        """ランダムなトピックを取得"""
        if not self.topics:
            return "今日はどんな一日でしたか？"
        return random.choice(self.topics)
    
    def suggest_topic(self):
        """会話のトピックを提案"""
        return self.get_random_topic()
    
    def record_game_result(self, game_type, score, total_questions, duration):
        """ゲーム結果を記録"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.game_results.append({
            "timestamp": timestamp,
            "game_type": game_type,
            "score": score,
            "total_questions": total_questions,
            "duration": duration
        })
    
    def save_session_to_csv(self):
        """セッションの内容をCSVに保存"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 会話履歴の保存
        if self.current_conversation:
            conversation_file = os.path.join(self.storage_dir, f"conversation_{timestamp}.csv")
            try:
                with open(conversation_file, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["時間", "話者", "内容"])
                    for entry in self.current_conversation:
                        writer.writerow([
                            entry["timestamp"],
                            entry["speaker"],
                            entry["text"]
                        ])
                print(f"会話履歴を保存しました: {conversation_file}")
            except Exception as e:
                print(f"会話履歴保存エラー: {e}")
        
        # ゲーム結果の保存
        if self.game_results:
            game_file = os.path.join(self.storage_dir, f"game_results_{timestamp}.csv")
            try:
                with open(game_file, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["時間", "ゲーム種類", "スコア", "問題数", "所要時間"])
                    for entry in self.game_results:
                        writer.writerow([
                            entry["timestamp"],
                            entry["game_type"],
                            entry["score"],
                            entry["total_questions"],
                            entry["duration"]
                        ])
                print(f"ゲーム結果を保存しました: {game_file}")
            except Exception as e:
                print(f"ゲーム結果保存エラー: {e}")
    
    def get_session_summary(self):
        """セッションの要約を取得"""
        now = datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M")
        
        summary_lines = [f"◆ セッション要約 ({now})"]
        
        # 会話の要約
        if self.current_conversation:
            user_messages = [msg for msg in self.current_conversation if msg["speaker"] == "user"]
            assistant_messages = [msg for msg in self.current_conversation if msg["speaker"] == "assistant"]
            
            summary_lines.append(f"会話回数: {len(user_messages)}回")
            
            if user_messages:
                summary_lines.append(f"最初の会話: {user_messages[0]['text'][:30]}...")
                summary_lines.append(f"最後の会話: {user_messages[-1]['text'][:30]}...")
        
        # ゲーム結果の要約
        if self.game_results:
            game_types = defaultdict(list)
            for result in self.game_results:
                game_types[result["game_type"]].append(result["score"])
            
            summary_lines.append(f"プレイしたゲーム: {len(self.game_results)}回")
            
            for game_type, scores in game_types.items():
                avg_score = sum(scores) / len(scores)
                summary_lines.append(f"{game_type}の平均スコア: {avg_score:.1f}")
        
        return "\n".join(summary_lines)
    
    def get_previous_summaries(self, count=3):
        """過去の会話要約を取得"""
        if not self.summaries:
            return ""
        
        # 最新のcount件の要約を取得
        recent_summaries = self.summaries[-count:]
        result = []
        
        for summary in recent_summaries:
            timestamp = datetime.datetime.strptime(summary["timestamp"], "%Y-%m-%d %H:%M:%S")
            formatted_date = timestamp.strftime("%Y年%m月%d日")
            result.append(f"[{formatted_date}] {summary['text']}")
        
        return "\n\n".join(result)
    
    def reset_session(self):
        """セッションをリセット"""
        self.save_session_to_csv()
        self.current_conversation = []
        self.game_results = []

    def load_conversation_history(self):
        """過去の会話履歴を読み込む"""
        history_files = sorted(
            [f for f in os.listdir(self.storage_dir) if f.startswith("conversation_") and f.endswith(".json")],
            reverse=True
        )
        
        all_topics = []
        for file in history_files[:5]:  # 最新5件の会話履歴を読み込む
            try:
                with open(os.path.join(self.storage_dir, file), "r", encoding="utf-8") as f:
                    history = json.load(f)
                    # ユーザーの発言からトピックを抽出
                    for message in history:
                        if message["role"] == "user":
                            text = message["content"]
                            if len(text) > 5 and not any(word in text for word in ["うん", "はい", "そうですね", "なるほど"]):
                                if "？" not in text and "?" not in text:
                                    all_topics.append(text)
            except Exception as e:
                print(f"会話履歴読み込みエラー: {e}")
        
        # 重複を除去して保存
        self.topics = list(set(all_topics))
        self.save_topics() 