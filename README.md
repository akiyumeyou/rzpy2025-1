# 音声会話アシスタント

高齢者向けの音声会話アシスタントプログラムです。

## 機能

- 音声認識（Whisperを使用）
- 自然な会話応答（GPT-4を使用）
- 音声合成
- 会話履歴の保存と要約

## 必要条件

### ハードウェア
- ラズベリーパイ（推奨：Raspberry Pi 4）
- マイク
- スピーカー

### ソフトウェア
- Python 3.10以上
- 必要なパッケージ（requirements.txt参照）

## インストール手順

1. システムパッケージのインストール
```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev portaudio19-dev
```

2. Pythonパッケージのインストール
```bash
pip3 install -r requirements.txt
```

3. 環境変数の設定
```bash
cp .env.example .env
# .envファイルを編集してAPIキーを設定
```

4. 音声デバイスの設定
```bash
# マイクの確認
arecord -l

# スピーカーの確認
aplay -l
```

## 使用方法

```bash
python3 api_chat.py
```

## 注意事項

- OpenAI APIキーが必要です
- インターネット接続が必要です
- 音声デバイスの設定が必要です

## トラブルシューティング

### 音声認識が動作しない場合
1. マイクの接続を確認
2. 音量設定を確認
3. デバイスIDを確認

### 音声合成が動作しない場合
1. スピーカーの接続を確認
2. 音量設定を確認
3. デバイスIDを確認

## ライセンス

MIT License 