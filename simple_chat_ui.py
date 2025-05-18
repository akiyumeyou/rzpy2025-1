#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import scrolledtext, font
import threading
import time
import queue
import api_chat  # 既存のAPI会話機能をインポート
import subprocess
import sys
import webbrowser
import voice_calc_game
import pygame
import platform

# モード選択肢
MODES = [
    "おしゃべり",
    "脳トレゲーム",
    "ポッツに接続",
    "終了します"
]

# VL Gothicフォントパス（ラズパイ標準）
# FONT_PATH = "/usr/share/fonts/truetype/vlgothic/VL-Gothic-Regular.ttf"

# フォントパスを自動判定
VL_GOTHIC_LOCAL = "/usr/share/fonts/truetype/vlgothic/VL-Gothic-Regular.ttf"
VL_GOTHIC_SYS = "/usr/share/fonts/truetype/vlgothic/VL-Gothic-Regular.ttf"
MAC_FONT = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"

if platform.system() == "Darwin":
    FONT_PATH = MAC_FONT
else:
    FONT_PATH = VL_GOTHIC_LOCAL

class SimpleChatUI:
    def __init__(self, root, standalone=True):
        self.root = root
        self.standalone = standalone
        self.root.title("音声会話アシスタント")
        self.root.geometry("800x600")  # 大きな画面サイズ
        #self.root.configure(bg="#F0F0F0")  # 背景色
        self.root.configure(bg="#FFFFFF")
        
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

class SimpleDisplayUI:
    def __init__(self, root):
        self.root = root
        self.root.title("モード選択")
        self.root.geometry("1000x700")
        self.root.configure(bg="#FFFFFF")
        self.current_frame = None
        self.mode = None
        self.question_no = 0
        self.last_result = ""
        self.create_mode_select()
        print("モード選択画面を表示")
        
    def clear_frame(self):
        if self.current_frame:
            self.current_frame.destroy()
            self.current_frame = None

    def create_mode_select(self):
        self.clear_frame()
        self.mode = None
        frame = tk.Frame(self.root, bg="#F8F8F8")
        frame.pack(expand=True, fill=tk.BOTH)
        self.current_frame = frame
        label = tk.Label(
            frame,
            text="モードを選んでください",
            font=("Helvetica", 48, "bold"),
            bg="#F8F8F8",
            fg="#222"
        )
        label.pack(pady=60)
        for mode in MODES:
            mode_label = tk.Label(
                frame,
                text=mode,
                font=("Helvetica", 40),
                bg="#F8F8F8",
                fg="#444"
            )
            mode_label.pack(pady=20)
        # 音声認識で選択を開始
        threading.Thread(target=self.listen_mode_select, daemon=True).start()

    def listen_mode_select(self):
        import speech_input
        import speech_output
        speech_output.speak("おしゃべり、脳トレゲーム、ポッツに接続、または終了しますか？")
        while True:
            user_input = speech_input.listen()
            if not user_input:
                continue
            normalized = user_input.replace(" ", "").replace("　", "")
            if any(word in normalized for word in ["終了", "さようなら", "終わります", "終了します"]):
                self.show_exit()
                return
            elif "おしゃべり" in normalized:
                self.show_chat()
                return
            elif "脳トレ" in normalized or "ゲーム" in normalized:
                self.show_calc_game()
                return
            elif "ポッツ" in normalized or "接続" in normalized:
                self.show_potz()
                return
            else:
                speech_output.speak("もう一度お願いします。おしゃべり、脳トレゲーム、ポッツに接続、または終了しますか？")

    def show_chat(self):
        self.clear_frame()
        self.mode = "chat"
        frame = tk.Frame(self.root, bg="#F8F8F8")
        frame.pack(expand=True, fill=tk.BOTH)
        self.current_frame = frame
        status_label = tk.Label(
            frame,
            text="声を聞いています",
            font=("Helvetica", 44, "bold"),
            bg="#F8F8F8",
            fg="#1976D2"
        )
        status_label.pack(pady=60)
        self.chat_response_label = tk.Label(
            frame,
            text="",
            font=("Helvetica", 40),
            bg="#F8F8F8",
            fg="#333"
        )
        self.chat_response_label.pack(pady=40)
        threading.Thread(target=self.run_chat, daemon=True).start()

    def run_chat(self):
        import speech_input
        import speech_output
        history = api_chat.ConversationHistory()
        while True:
            self.set_chat_status("声を聞いています")
            user_input = speech_input.listen()
            if not user_input:
                continue
            if "終了" in user_input:
                speech_output.speak("会話を終了します。")
                self.create_mode_select()
                return
            history.add_message("user", user_input)
            response = api_chat.generate_response(user_input, history)
            if response:
                response = api_chat.postprocess_response(response)
                self.set_chat_response(response)
                speech_output.speak(response)
                history.add_message("assistant", response)
            time.sleep(0.5)

    def set_chat_status(self, text):
        if hasattr(self, 'chat_response_label'):
            self.chat_response_label.master.children['!label'].config(text=text)

    def set_chat_response(self, text):
        if hasattr(self, 'chat_response_label'):
            self.chat_response_label.config(text=text)

    def show_calc_game(self):
        self.clear_frame()
        self.mode = "calc"
        frame = tk.Frame(self.root, bg="#F8F8F8")
        frame.pack(expand=True, fill=tk.BOTH)
        self.current_frame = frame
        self.calc_question_label = tk.Label(
            frame,
            text="",
            font=("Helvetica", 44, "bold"),
            bg="#F8F8F8",
            fg="#388E3C"
        )
        self.calc_question_label.pack(pady=60)
        self.calc_result_label = tk.Label(
            frame,
            text="",
            font=("Helvetica", 40),
            bg="#F8F8F8",
            fg="#333"
        )
        self.calc_result_label.pack(pady=40)
        threading.Thread(target=self.run_calc_game, daemon=True).start()

    def run_calc_game(self):
        import speech_input
        import speech_output
        game = voice_calc_game.VoiceCalculationGame()
        total_questions = 10
        score = 0
        for i in range(1, total_questions + 1):
            level = 1 if i <= 5 else 2
            question, answer = game.generate_question(level=level)
            self.set_calc_question(f"第{i}問目: {question}")
            self.set_calc_result("")
            speech_output.speak(question)
            response = speech_input.listen()
            if not response:
                speech_output.speak("もう一度同じ問題を出します。")
                speech_output.speak(question)
                response = speech_input.listen()
                if not response:
                    self.set_calc_result("スキップ")
                    continue
            if "終了" in response:
                self.set_calc_result("終了します")
                speech_output.speak("ゲームを終了します。")
                self.create_mode_select()
                return
            try:
                user_answer = voice_calc_game.japanese_number_to_int(response)
                if user_answer == answer:
                    self.set_calc_result("正解！")
                    speech_output.speak("正解です！")
                    score += 1
                else:
                    self.set_calc_result(f"不正解（正解: {answer}）")
                    speech_output.speak(f"残念、正解は{answer}でした。")
            except Exception:
                self.set_calc_result("無効な回答")
                speech_output.speak("数字で答えてください。")
            time.sleep(1)
        self.set_calc_question("")
        self.set_calc_result(f"ゲーム終了！{score}問正解でした。")
        speech_output.speak(f"ゲーム終了です。{score}問正解でした。お疲れ様でした。")
        time.sleep(2)
        self.create_mode_select()

    def set_calc_question(self, text):
        if hasattr(self, 'calc_question_label'):
            self.calc_question_label.config(text=text)

    def set_calc_result(self, text):
        if hasattr(self, 'calc_result_label'):
            self.calc_result_label.config(text=text)

    def show_potz(self):
        self.clear_frame()
        frame = tk.Frame(self.root, bg="#F8F8F8")
        frame.pack(expand=True, fill=tk.BOTH)
        self.current_frame = frame
        label = tk.Label(
            frame,
            text="ポッツに接続中...",
            font=("Helvetica", 48, "bold"),
            bg="#F8F8F8",
            fg="#1976D2"
        )
        label.pack(pady=120)
        webbrowser.open("https://ftc.potz.jp/dashboard")
        self.root.after(3000, self.create_mode_select)

    def show_exit(self):
        self.clear_frame()
        frame = tk.Frame(self.root, bg="#F8F8F8")
        frame.pack(expand=True, fill=tk.BOTH)
        self.current_frame = frame
        label = tk.Label(
            frame,
            text="終了します",
            font=("Helvetica", 48, "bold"),
            bg="#F8F8F8",
            fg="#B71C1C"
        )
        label.pack(pady=120)
        self.root.after(2000, self.root.quit)

class PygameUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1000, 700))
        pygame.display.set_caption("モード選択")
        self.font_title = pygame.font.Font(FONT_PATH, 60)
        self.font_item = pygame.font.Font(FONT_PATH, 48)
        self.font_status = pygame.font.Font(FONT_PATH, 44)
        self.font_result = pygame.font.Font(FONT_PATH, 40)
        self.state = "menu"  # menu, chat, calc, potz, exit
        self.chat_response = ""
        self.calc_question = ""
        self.calc_result = ""
        self.calc_score = 0
        self.calc_no = 1
        self.running = True
        self.listen_thread = None
        self.bg_color = (255, 255, 255)
        self.fg_color = (30, 30, 30)
        self.start_menu()

    def start_menu(self):
        self.state = "menu"
        self.chat_response = ""
        self.calc_question = ""
        self.calc_result = ""
        self.calc_score = 0
        self.calc_no = 1
        if self.listen_thread and self.listen_thread.is_alive():
            self.listen_thread = None
        self.listen_thread = threading.Thread(target=self.listen_menu, daemon=True)
        self.listen_thread.start()

    def listen_menu(self):
        import speech_input
        import speech_output
        speech_output.speak("おしゃべり、脳トレゲーム、ポッツに接続、または終了しますか？")
        while self.state == "menu":
            user_input = speech_input.listen()
            if not user_input:
                continue
            normalized = user_input.replace(" ", "").replace("　", "")
            if any(word in normalized for word in ["終了", "さようなら", "終わります", "終了します"]):
                self.state = "exit"
                return
            elif "おしゃべり" in normalized:
                self.state = "chat"
                self.start_chat()
                return
            elif "脳トレ" in normalized or "ゲーム" in normalized:
                self.state = "calc"
                self.start_calc()
                return
            elif "ポッツ" in normalized or "接続" in normalized:
                self.state = "potz"
                self.start_potz()
                return
            else:
                speech_output.speak("もう一度お願いします。おしゃべり、脳トレゲーム、ポッツに接続、または終了しますか？")

    def start_chat(self):
        self.chat_response = ""
        if self.listen_thread and self.listen_thread.is_alive():
            self.listen_thread = None
        self.listen_thread = threading.Thread(target=self.run_chat, daemon=True)
        self.listen_thread.start()

    def run_chat(self):
        import speech_input
        import speech_output
        history = api_chat.ConversationHistory()
        while self.state == "chat":
            self.chat_response = ""
            user_input = speech_input.listen()
            if not user_input:
                continue
            if "終了" in user_input:
                speech_output.speak("会話を終了します。")
                self.start_menu()
                return
            history.add_message("user", user_input)
            response = api_chat.generate_response(user_input, history)
            if response:
                response = api_chat.postprocess_response(response)
                self.chat_response = response
                speech_output.speak(response)
                history.add_message("assistant", response)
            time.sleep(0.5)

    def start_calc(self):
        self.calc_score = 0
        self.calc_no = 1
        self.calc_question = ""
        self.calc_result = ""
        if self.listen_thread and self.listen_thread.is_alive():
            self.listen_thread = None
        self.listen_thread = threading.Thread(target=self.run_calc, daemon=True)
        self.listen_thread.start()

    def run_calc(self):
        import speech_input
        import speech_output
        game = voice_calc_game.VoiceCalculationGame()
        total_questions = 10
        for i in range(1, total_questions + 1):
            if self.state != "calc":
                return
            level = 1 if i <= 5 else 2
            question, answer = game.generate_question(level=level)
            self.calc_question = f"第{i}問目: {question}"
            self.calc_result = ""
            speech_output.speak(question)
            response = speech_input.listen()
            if not response:
                speech_output.speak("もう一度同じ問題を出します。")
                speech_output.speak(question)
                response = speech_input.listen()
                if not response:
                    self.calc_result = "スキップ"
                    continue
            if "終了" in response:
                self.calc_result = "終了します"
                speech_output.speak("ゲームを終了します。")
                self.start_menu()
                return
            try:
                user_answer = voice_calc_game.japanese_number_to_int(response)
                if user_answer == answer:
                    self.calc_result = "正解！"
                    speech_output.speak("正解です！")
                    self.calc_score += 1
                else:
                    self.calc_result = f"不正解（正解: {answer}）"
                    speech_output.speak(f"残念、正解は{answer}でした。")
            except Exception:
                self.calc_result = "無効な回答"
                speech_output.speak("数字で答えてください。")
            time.sleep(1)
        self.calc_question = ""
        self.calc_result = f"ゲーム終了！{self.calc_score}問正解でした。"
        speech_output.speak(f"ゲーム終了です。{self.calc_score}問正解でした。お疲れ様でした。")
        time.sleep(2)
        self.start_menu()

    def start_potz(self):
        self.state = "potz"
        webbrowser.open("https://ftc.potz.jp/dashboard")
        threading.Thread(target=self.potz_wait_and_return, daemon=True).start()

    def potz_wait_and_return(self):
        time.sleep(3)
        self.start_menu()

    def mainloop(self):
        clock = pygame.time.Clock()
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            self.screen.fill(self.bg_color)
            if self.state == "menu":
                self.draw_menu()
            elif self.state == "chat":
                self.draw_chat()
            elif self.state == "calc":
                self.draw_calc()
            elif self.state == "potz":
                self.draw_potz()
            elif self.state == "exit":
                self.draw_exit()
                pygame.display.update()
                time.sleep(2)
                self.running = False
                break
            pygame.display.update()
            clock.tick(30)
        pygame.quit()
        sys.exit()

    def draw_menu(self):
        title = self.font_title.render("モードを選んでください", True, self.fg_color)
        self.screen.blit(title, (120, 80))
        for i, mode in enumerate(MODES):
            text = self.font_item.render(mode, True, (50, 50, 50))
            self.screen.blit(text, (200, 200 + i * 100))

    def draw_chat(self):
        status = self.font_status.render("声を聞いています", True, (25, 90, 180))
        self.screen.blit(status, (180, 120))
        if self.chat_response:
            self.draw_text(
                self.screen,
                self.chat_response,
                self.font_result,
                (30, 30, 30),
                120, 300,
                max_width=760
            )

    def draw_calc(self):
        if self.calc_question:
            q = self.font_status.render(self.calc_question, True, (30, 120, 60))
            self.screen.blit(q, (100, 120))
        if self.calc_result:
            self.draw_text(
                self.screen,
                self.calc_result,
                self.font_result,
                (30, 30, 30),
                120, 300,
                max_width=760
            )

    def draw_potz(self):
        label = self.font_title.render("ポッツに接続中...", True, (25, 90, 180))
        self.screen.blit(label, (180, 220))

    def draw_exit(self):
        label = self.font_title.render("終了します", True, (180, 30, 30))
        self.screen.blit(label, (320, 220))

    def draw_text(self, surface, text, font, color, x, y, max_width):
        """指定幅で自動折り返ししてテキストを描画"""
        lines = []
        line = ""
        for char in text:
            test_line = line + char
            if font.size(test_line)[0] > max_width:
                lines.append(line)
                line = char
            else:
                line = test_line
        if line:
            lines.append(line)
        for i, l in enumerate(lines):
            rendered = font.render(l, True, color)
            surface.blit(rendered, (x, y + i * font.get_linesize()))

def main():
    ui = PygameUI()
    ui.mainloop()

if __name__ == "__main__":
    main() 