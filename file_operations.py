import csv
import json
import subprocess
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from langchain_openai import ChatOpenAI
import os

SERVICE_ACCOUNT_FILE = "rzpi_chat.json"
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

# 会話の内容をCSVに保存する関数
def save_conversation_to_csv(conversations):
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"conversation_{now}.csv"
    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["User", "AI"])  # ヘッダー
            writer.writerows(conversations)  # 会話をCSVに書き込み
        print(f"Saved conversation to {filename}")
    except Exception as e:
        print(f"Failed to save conversation to CSV: {e}")
    return filename

# Node.jsスクリプトを実行して会話要約を生成する関数
def run_js_summary_script(conversations):
    try:
        # 会話リストをCSVに保存
        csv_filename = save_conversation_to_csv(conversations)
        
        # Node.js スクリプトを呼び出し
        result = subprocess.run(
            ['node', 'sum.js', csv_filename],  # CSVファイルのパスを引数として渡す
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"Node.js script error: {result.stderr}")
            raise Exception(f"Node.js script error: {result.stderr}")

        print(f"Node.js script output: {result.stdout}")
        return result.stdout.strip()  # 要約結果を返す
    except Exception as e:
        print(f"Failed to run JS script: {e}")
        return None

# スプレッドシートに要約を追加する関数
def append_summary_to_sheet(summary):
    try:
        # Google Sheets API および Google Drive API のスコープと認証情報を設定
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
        
        # 認証してGoogleスプレッドシートにアクセス
        client = gspread.authorize(credentials)
        
        # スプレッドシート名を指定（"conversation_log"）
        sheet = client.open("conversation_log").sheet1  # シートの名前が "Sheet1" の場合
        
        # 現在の日時と要約を取得
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # スプレッドシートに新しい行を追加（新しいデータは下に追加される）
        sheet.append_row([now, summary])
        print(f"Appended summary to Google Sheets")  # デバッグ用ログ
    except Exception as e:
        print(f"Failed to append to Google Sheets: {e}")  # デバッグ用ログ

def save_conversation_summary(history, start_time, end_time):
    """
    Sheet1に、1セッションごとに1行、
    日時・会話時間・ユーザー発話要約・感情キーワードを保存
    """
    # ユーザー発話のみ抽出
    user_texts = [msg['content'] for msg in history if msg.get('role') == 'user']
    if not user_texts:
        print("ユーザー発話がありません")
        return False
    user_text = "\n".join(user_texts)

    # 会話時間計算
    duration = end_time - start_time
    minutes = int(duration // 60)
    seconds = int(duration % 60)
    conversation_time = f"{minutes}分{seconds}秒"

    # LangChain+OpenAIで要約・感情分析
    llm = ChatOpenAI(model="gpt-4", temperature=0.7, max_tokens=200)
    prompt = f"""
    会話の中で伝えたかったことを150文字以内で要約してください。
    感情や重要なポイントをピックアップしてください。
    AIの応答内容は無視してください。
    ほっこりするメッセージにしてください。
    最後の終了コマンドは無視してください。
    ユーザー発話:
    {user_text}
    """
    try:
        summary_resp = llm.invoke(prompt)
        summary = summary_resp.content.strip()
    except Exception as e:
        print(f"要約生成エラー: {e}")
        summary = "要約生成に失敗しました"

    # 感情キーワード抽出
    emotion_prompt = f"""
    以下のユーザー発話から感情キーワード（例：楽しい、寂しい、嬉しい、悲しいなど）を3つ以内で抽出し、カンマ区切りで出力してください。
    ユーザー発話:
    {user_text}
    """
    try:
        emotion_resp = llm.invoke(emotion_prompt)
        emotions = emotion_resp.content.strip().replace("。", "").replace("、", ",")
    except Exception as e:
        print(f"感情抽出エラー: {e}")
        emotions = ""

    # Google Sheets保存
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
        client = gspread.authorize(credentials)
        
        # スプレッドシートを開く
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        print(f"使用中のGoogleシートID: {GOOGLE_SHEET_ID}")
        
        # 既存のシートを確認
        worksheet_list = spreadsheet.worksheets()
        sheet_names = [ws.title.lower() for ws in worksheet_list]
        print(f"既存のシート一覧: {sheet_names}")
        
        # シート名を正規化（小文字に統一）
        target_sheet_name = "sheet1"
        
        # シートの取得または作成
        sheet = None
        for ws in worksheet_list:
            if ws.title.lower() == target_sheet_name:
                sheet = ws
                print(f"既存の{ws.title}を使用します")
                break
        
        if sheet is None:
            print(f"{target_sheet_name}が見つからないため、新規作成します")
            try:
                sheet = spreadsheet.add_worksheet(title=target_sheet_name, rows="1000", cols="20")
                print(f"{target_sheet_name}を新規作成しました")
                # ヘッダー行を追加
                sheet.append_row(["日時", "会話時間", "要約", "感情キーワード"])
            except Exception as e:
                print(f"シート作成エラー: {e}")
                return False
        
        # データを保存
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([now, conversation_time, summary, emotions])
        print(f"{sheet.title}に会話履歴を保存しました")
        return True
        
    except Exception as e:
        import traceback
        print(f"Google Sheets保存エラー: {e}")
        traceback.print_exc()
        return False

def save_conversation_record(history):
    # 必要に応じて実装
    print("save_conversation_recordが呼ばれました（ダミー）")
    return True

def save_calc_game_result(start_time, end_time, score, total_questions, detail_results):
    """
    Sheet2に、脳トレゲームの実施日時・所要時間・スコア・詳細結果を保存
    """
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
        client = gspread.authorize(credentials)
        
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        worksheet_list = spreadsheet.worksheets()
        sheet_names = [ws.title.lower() for ws in worksheet_list]
        target_sheet_name = "sheet2"
        
        # シートの取得または作成
        sheet = None
        for ws in worksheet_list:
            if ws.title.lower() == target_sheet_name:
                sheet = ws
                break
        if sheet is None:
            sheet = spreadsheet.add_worksheet(title=target_sheet_name, rows="1000", cols="20")
            # ヘッダー行を追加
            sheet.append_row(["実施日時", "所要時間", "スコア", "詳細"])
        
        # 所要時間計算
        duration = end_time - start_time
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        play_time = f"{minutes}分{seconds}秒"
        
        # 実施日時
        exec_time = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")
        
        # 詳細（リストを1つの文字列にまとめる）
        detail_str = "; ".join(detail_results)
        
        # データを保存
        sheet.append_row([exec_time, play_time, f"{score}/{total_questions}", detail_str])
        print(f"{sheet.title}に脳トレゲーム結果を保存しました")
        return True
    except Exception as e:
        import traceback
        print(f"Google Sheets保存エラー: {e}")
        traceback.print_exc()
        return False
