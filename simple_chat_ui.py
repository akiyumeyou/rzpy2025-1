#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import scrolledtext, font
import threading
import time
import queue
import api_chat  # 既存のAPI会話機能をインポート
import subprocess

class SimpleChatUI:
    def __init__(self, root, standalone=True):
        self.root = root
        self.standalone = standalone
        self.root.title("音声会話アシスタント")
        self.root.geometry("800x600")  # 大きな画面サイズ
        self.root.configure(bg="#F0F0F0")  # 背景色
        
        # メッセージキュー
        self.message_queue = queue.Queue()
        
        # フォント設定（大きく）
        self.title_font = font.Font(family="Helvetica", size=32, weight="bold")
        self.text_font = font.Font(family="Helvetica", size=22)
        self.button_font = font.Font(family="Helvetica", size=24, weight="bold")
        
        self.create_widgets()
        
        # メッセージ処理スレッド
        self.stop_event = threading.Event()
        self.ui_update_thread = threading.Thread(target=self.update_ui)
        self.ui_update_thread.daemon = True
        self.ui_update_thread.start()
        
        # 終了時の処理を登録
        if self.standalone:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 会話スレッド
        self.conversation_thread = None
        
    def create_widgets(self):
        # タイトルラベル
        title_frame = tk.Frame(self.root, bg="#F0F0F0")
        title_frame.pack(pady=20)
        
        title_label = tk.Label(
            title_frame, 
            text="おしゃべりアシスタント", 
            font=self.title_font,
            bg="#F0F0F0", 
            fg="#333333"
        )
        title_label.pack()
        
        # 会話表示エリア
        chat_frame = tk.Frame(self.root, bg="#F0F0F0")
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            font=self.text_font,
            bg="white",
            fg="#333333",
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # ステータス表示
        status_frame = tk.Frame(self.root, bg="#F0F0F0")
        status_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.status_label = tk.Label(
            status_frame,
            text="会話の内容がここに表示されます",
            font=self.text_font,
            bg="#E0E0E0",
            fg="#333333",
            width=50,
            height=2
        )
        self.status_label.pack()
        
        # 操作ボタンフレーム
        button_frame = tk.Frame(self.root, bg="#F0F0F0")
        button_frame.pack(pady=20)
        
        # メインメニューに戻るボタン（スタンドアロンモードでなければ表示）
        if not self.standalone:
            self.back_button = tk.Button(
                button_frame,
                text="メニューに戻る",
                font=self.button_font,
                bg="#2196F3",
                fg="white",
                width=16,
                height=2,
                command=self.back_to_main
            )
            self.back_button.pack(padx=10)
    
    def update_ui(self):
        """UIを更新するスレッド"""
        while not self.stop_event.is_set():
            try:
                # キューからメッセージを取得
                if not self.message_queue.empty():
                    msg_type, msg_text = self.message_queue.get(block=False)
                    self.add_message(msg_type, msg_text)
                    self.message_queue.task_done()
                time.sleep(0.1)
            except Exception as e:
                print(f"UI更新エラー: {e}")
                time.sleep(1)
    
    def add_message(self, speaker, message):
        """会話表示エリアにメッセージを追加"""
        self.chat_display.config(state=tk.NORMAL)
        
        # 話者に合わせて色を変更
        if speaker == "system":
            # システムメッセージは「アシスタント」として表示
            self.chat_display.insert(tk.END, "アシスタント: ", "assistant")
            tag = "assistant_msg"
        elif speaker == "user":
            self.chat_display.insert(tk.END, "あなた: ", "user")
            tag = "user_msg"
        elif speaker == "assistant":
            self.chat_display.insert(tk.END, "アシスタント: ", "assistant")
            tag = "assistant_msg"
        else:
            self.chat_display.insert(tk.END, f"{speaker}: ", "other")
            tag = "other_msg"
        
        # メッセージ本文
        self.chat_display.insert(tk.END, f"{message}\n\n", tag)
        
        # タグの設定
        self.chat_display.tag_config("system", foreground="#006600", font=self.text_font)
        self.chat_display.tag_config("user", foreground="#0066CC", font=self.text_font)
        self.chat_display.tag_config("assistant", foreground="#006600", font=self.text_font)
        self.chat_display.tag_config("other", foreground="#333333", font=self.text_font)
        
        self.chat_display.tag_config("system_msg", foreground="#333333", font=self.text_font)
        self.chat_display.tag_config("user_msg", foreground="#333333", font=self.text_font)
        self.chat_display.tag_config("assistant_msg", foreground="#333333", font=self.text_font)
        self.chat_display.tag_config("other_msg", foreground="#333333", font=self.text_font)
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)  # 最新メッセージまでスクロール
        
        # ステータスラベルを更新
        self.update_status("会話中...")
    
    def update_status(self, status):
        """ステータス表示を更新"""
        self.status_label.config(text=status)
    
    def start_conversation(self):
        """会話を開始"""
        # すでに会話が始まっている場合は何もしない
        if self.conversation_thread and self.conversation_thread.is_alive():
            return
            
        self.update_status("会話を開始しています...")
        
        # チャット表示をクリア
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
        # 会話スレッドを開始
        self.conversation_thread = threading.Thread(target=self.run_conversation)
        self.conversation_thread.daemon = True
        self.conversation_thread.start()
    
    def run_conversation(self):
        """会話処理を実行"""
        try:
            # オリジナルの関数をオーバーライド
            def custom_speak(text, wait=True):
                # UIにメッセージを追加
                self.message_queue.put(("assistant", text))
                # 元の関数を呼び出し
                try:
                    # 再帰呼び出しを防ぐために直接subprocess呼び出し
                    print(f"アシスタント: {text}")
                    # 会話を記録
                    api_chat.conversation_manager.add_to_conversation("assistant", text)
                    
                    # AIが話し始めるフラグをセット
                    api_chat.gpt_speaking = True
                    
                    # 「は」を「わ」と発音させるための置換
                    speaking_text = text.replace("は", "わ").replace("初めましょう", "はじめましょう")
                    
                    # 句読点で区切って発話をより自然にする
                    for mark in ["。", "、", "！", "？"]:
                        speaking_text = speaking_text.replace(mark, mark + " ")
                    
                    # macOSのsayコマンドを使用
                    if wait:
                        subprocess.run(["say", "-v", "Kyoko", "-r", "140", speaking_text])
                        api_chat.gpt_speaking = False
                    else:
                        # 待たずに次の処理に進む
                        process = subprocess.Popen(["say", "-v", "Kyoko", "-r", "140", speaking_text])
                        # 非同期で終了を検知
                        def monitor_process():
                            process.wait()
                            api_chat.gpt_speaking = False
                        threading.Thread(target=monitor_process, daemon=True).start()
                    
                    # 最後の活動時間を更新
                    api_chat.last_activity_time = time.time()
                    return None
                except Exception as e:
                    print(f"音声出力エラー: {e}")
                    api_chat.gpt_speaking = False
                    return None
            
            def custom_say_system_message(message, wait=True):
                """システムメッセージを発話する（相槌など）"""
                # 相槌は画面に表示しない（短いメッセージは相槌と見なす）
                if len(message) <= 10 and any(word in message for word in ["うん", "はい", "そうですね", "なるほど"]):
                    # 相槌は表示しない
                    pass
                else:
                    # システムメッセージとして表示（トピック提案など長めのメッセージ）
                    self.message_queue.put(("system", message))
                
                try:
                    # 再帰呼び出しを防ぐために直接処理
                    print(f"システム: {message}")
                    
                    # AIが話し始めるフラグをセット（相槌でも設定）
                    api_chat.gpt_speaking = True
                    
                    # 会話を記録
                    api_chat.conversation_manager.add_to_conversation("system", message)
                    
                    # 「は」を「わ」と発音させるための置換
                    speaking_text = message.replace("は", "わ").replace("初めましょう", "はじめましょう")
                    
                    # 句読点で区切って発話をより自然にする
                    for mark in ["。", "、", "！", "？"]:
                        speaking_text = speaking_text.replace(mark, mark + " ")
                    
                    # macOSのsayコマンドを使用
                    if wait:
                        subprocess.run(["say", "-v", "Kyoko", "-r", "140", speaking_text])
                        api_chat.gpt_speaking = False
                    else:
                        # 待たずに次の処理に進む
                        process = subprocess.Popen(["say", "-v", "Kyoko", "-r", "140", speaking_text])
                        # 非同期で終了を検知
                        def monitor_process():
                            process.wait()
                            api_chat.gpt_speaking = False
                        threading.Thread(target=monitor_process, daemon=True).start()
                    
                    # 最後の活動時間を更新
                    api_chat.last_activity_time = time.time()
                except Exception as e:
                    print(f"システムメッセージ発話中にエラーが発生しました: {e}")
                    api_chat.gpt_speaking = False
            
            # 関数をオーバーライド
            original_speak = api_chat.speak
            original_say_system = api_chat.say_system_message
            
            api_chat.speak = custom_speak
            api_chat.say_system_message = custom_say_system_message
            
            # ユーザー発話を取得する関数をオーバーライド
            original_listen = api_chat.listen
            
            def custom_listen(conversation_history):
                # UIのステータスを更新
                self.root.after(0, lambda: self.update_status("聞いています..."))
                # 元の関数を呼び出し
                try:
                    text = original_listen(conversation_history)
                    if text:
                        # UIにメッセージを追加（短すぎる相槌っぽいものは非表示）
                        if len(text) > 2:  # 短すぎる応答は表示しない
                            self.message_queue.put(("user", text))
                    return text
                except Exception as e:
                    print(f"音声認識エラー: {e}")
                    self.root.after(0, lambda: self.update_status("音声認識エラー"))
                    return None
            
            api_chat.listen = custom_listen
            
            # 会話処理を実行
            self.root.after(0, lambda: self.update_status("会話を始めます..."))
            
            # 会話の初期化（歓迎メッセージは表示しない - API側で対応）
            
            # APIを使った会話を開始
            api_chat.start_voice_chat()
            
            # 元の関数を復元
            api_chat.speak = original_speak
            api_chat.say_system_message = original_say_system
            api_chat.listen = original_listen
            
            # 終了ステータスを表示
            self.root.after(0, lambda: self.update_status("会話が終了しました。メニューに戻るには戻るボタンを押してください。"))
            
        except Exception as e:
            print(f"会話エラー: {e}")
            self.root.after(0, lambda: self.update_status(f"エラーが発生しました: {e}"))
    
    def back_to_main(self):
        """メインメニューに戻る"""
        # 会話が実行中なら終了
        if self.conversation_thread and self.conversation_thread.is_alive():
            # 会話を終了
            api_chat.last_activity_time = time.time()
            api_chat.silence_counter = 0
            
            # 少し待つ
            self.update_status("会話を終了しています...")
            time.sleep(0.5)
        
        # 親ウィンドウに戻る準備
        self.update_status("メインメニューに戻ります...")
        self.stop_event.set()  # UIの更新スレッドを停止
        
        # rootウィンドウを閉じる（親ウィンドウは残る）
        self.root.destroy()
    
    def on_closing(self):
        """アプリケーション終了時の処理"""
        # 会話が実行中なら終了
        if self.conversation_thread and self.conversation_thread.is_alive():
            # 会話を終了
            api_chat.last_activity_time = time.time()
            api_chat.silence_counter = 0
        
        self.stop_event.set()
        self.root.destroy()

def main():
    """スタンドアロンモードで実行する場合のエントリポイント"""
    root = tk.Tk()
    app = SimpleChatUI(root, standalone=True)
    app.start_conversation()  # 自動的に会話を開始
    root.mainloop()

if __name__ == "__main__":
    main() 