#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import csv
import random
import datetime
from collections import defaultdict
import openai
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

class ConversationManager:
    def __init__(self, storage_dir="conversation_history"):
        """会話履歴管理クラスの初期化"""
        self.storage_dir = storage_dir
        self.current_conversation = []
        self.topics = []
        self.game_results = []
        self.summaries = []
        self.start_time = datetime.datetime.now()
        
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
        """会話履歴から新しい話題を提案"""
        try:
            if len(self.current_conversation) < 2:
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
            {self.current_conversation}
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": topic_prompt}],
                temperature=0.7,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"話題提案中にエラーが発生しました: {e}")
            return "話題の提案に失敗しました。"
    
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
        """会話セッションをCSVファイルに保存"""
        try:
            # 現在の日時を取得
            now = datetime.datetime.now()
            filename = f"conversation_log_{now.strftime('%Y%m%d_%H%M%S')}.csv"
            
            # CSVファイルに保存
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'role', 'content'])
                for msg in self.current_conversation:
                    writer.writerow([msg['timestamp'], msg['speaker'], msg['text']])
                    
            print(f"会話履歴を{filename}に保存しました")
            
        except Exception as e:
            print(f"会話履歴の保存中にエラーが発生しました: {e}")
    
    def get_session_summary(self):
        """セッションの要約を取得"""
        now = datetime.datetime.now()
        duration = now - self.start_time
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        
        summary_lines = [f"◆ セッション要約 ({now.strftime('%Y年%m月%d日 %H:%M')})"]
        summary_lines.append(f"実行時間: {hours}時間{minutes}分")
        
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
            
            summary_lines.append("\n◆ ゲーム結果")
            for game_type, scores in game_types.items():
                avg_score = sum(scores) / len(scores)
                summary_lines.append(f"{game_type}: 平均スコア {avg_score:.1f}点")
        
        return "\n".join(summary_lines)
    
    def get_previous_summaries(self, count=3):
        """過去の要約を取得"""
        return self.summaries[-count:] if self.summaries else []
    
    def reset_session(self):
        """セッションをリセット"""
        self.current_conversation = []
        self.game_results = []
        self.start_time = datetime.datetime.now()
    
    def load_conversation_history(self):
        """会話履歴を読み込む"""
        # 最新の会話履歴ファイルを探す
        conversation_files = [f for f in os.listdir(self.storage_dir) if f.startswith("conversation_")]
        if not conversation_files:
            return []
        
        latest_file = max(conversation_files)
        file_path = os.path.join(self.storage_dir, latest_file)
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return list(reader)
        except Exception as e:
            print(f"会話履歴読み込みエラー: {e}")
            return [] 