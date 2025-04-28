import random
from typing import Dict, List

# 感情表現と相槌のマッピング
EMOTION_RESPONSES: Dict[str, List[str]] = {
    "happy": [
        "それは良かったですね。",
        "嬉しい気持ちが伝わってきます。",
        "楽しい時間でしたね。",
        "素晴らしいですね。",
        "おめでとうございます。",
        "それは嬉しいですね。"
    ],
    "sad": [
        "それは大変でしたね…",
        "無理しないでくださいね。",
        "辛かったですね。",
        "お疲れ様でした。",
        "ゆっくり休んでくださいね。",
        "大丈夫ですか？"
    ],
    "interest": [
        "それは面白そうですね。",
        "興味深いですね。",
        "詳しく聞かせてください。",
        "それは気になりますね。",
        "もっと教えてください。"
    ],
    "question": [
        "うーん、どうなんでしょう？",
        "それは気になりますね。",
        "ちょっと考えちゃいますね。",
        "そうですね、どうなんでしょう。",
        "難しい質問ですね。"
    ]
}

# 感情キーワード
EMOTION_KEYWORDS: Dict[str, List[str]] = {
    "happy": ["楽しい", "嬉しい", "よかった", "面白い", "笑った", "幸せ", "うれしい", "楽しかった"],
    "sad": ["疲れた", "辛い", "寂しい", "悲しい", "痛い", "大変", "つらい", "しんどい"],
    "interest": ["面白い", "興味", "気になる", "好き", "楽しい", "おもしろい", "すごい"],
    "question": ["どう", "何", "知ってる", "わかる", "でしょう", "かな", "ですか", "か？", "できる", "できます"]
}

# デフォルトの相槌
DEFAULT_RESPONSES: List[str] = [
    "そうなんですね。",
    "うんうん。",
    "なるほど。",
    "はいはい。",
    "ふむふむ。",
    "そうですか。",
    "あ、そうなんですね。",
    "へえ、そうなんですか。",
    "そうですね。",
    "なるほど、そうなんですね。"
]

def select_local_aizuchi(user_input: str) -> str:
    # 感情キーワードの検出
    detected_emotions = []
    for emotion, keywords in EMOTION_KEYWORDS.items():
        if any(keyword in user_input for keyword in keywords):
            detected_emotions.append(emotion)

    # 感情に応じた相槌を選択
    if detected_emotions:
        # 複数の感情が検出された場合は、最初に検出された感情を使用
        emotion = detected_emotions[0]
        return random.choice(EMOTION_RESPONSES[emotion])

    # デフォルトの相槌を選択
    return random.choice(DEFAULT_RESPONSES)
