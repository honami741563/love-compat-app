# -*- coding: utf-8 -*-
"""
恋愛相性診断アプリ - 採点ロジック
仕様書 セクション3・4・5 に対応
"""

# Q1〜Q16 の質問文（表示用）。reverse=True は逆転項目。
QUESTIONS = [
    {"id": 1,  "text": "活発で、外向的だと思う",                                             "factor": "Extra",     "reverse": False},
    {"id": 2,  "text": "他人に批判的で、揉め事を起こしやすいと思う",                          "factor": "Agree",     "reverse": True},
    {"id": 3,  "text": "しっかりしていて、自分に厳しく計画的だと思う",                        "factor": "Consc",     "reverse": False},
    {"id": 4,  "text": "心配性で、気分が変わりやすいと思う",                                  "factor": "E_stabil",  "reverse": True},
    {"id": 5,  "text": "新しいことが好きで、発想が豊かな方だと思う",                          "factor": "Open",      "reverse": False},
    {"id": 6,  "text": "控えめで、静かな方だと思う",                                          "factor": "Extra",     "reverse": True},
    {"id": 7,  "text": "同情しやすく、心が優しい方だと思う",                                  "factor": "Agree",     "reverse": False},
    {"id": 8,  "text": "ずぼらで、最後までやり遂げないことが多い",                            "factor": "Consc",     "reverse": True},
    {"id": 9,  "text": "冷静で、感情が安定していると思う",                                    "factor": "E_stabil",  "reverse": False},
    {"id": 10, "text": "現実的で、あまり慣習に逆らわない方だ",                                "factor": "Open",      "reverse": True},
    {"id": 11, "text": "人と親しくなっても、「いつか離れていってしまうかも」と不安になることがある", "factor": "A_anxiety", "reverse": False},
    {"id": 12, "text": "大切な人が、自分と同じくらい自分のことを大事に思ってくれているか気になりやすい", "factor": "A_anxiety", "reverse": False},
    {"id": 13, "text": "人から悩み事を深く相談されたり、自分の弱みをさらけ出すのは少し苦手だ",  "factor": "A_avoid",   "reverse": False},
    {"id": 14, "text": "誰かとどんなに仲良くなっても、自分のプライベートな領域に踏み込まれると息苦しくなる", "factor": "A_avoid",   "reverse": False},
    {"id": 15, "text": "自分が本当に困ったときや傷ついたときは、意地を張らずに誰かを頼ることができる", "factor": "A_secure",  "reverse": False},
    {"id": 16, "text": "自分のダメな部分を知られても、受け入れてもらえるだろうという安心感がある", "factor": "A_secure",  "reverse": False},
]

DATING_CHOICES = [
    ("0", "0人"),
    ("1-2", "1〜2人"),
    ("3+", "3人以上"),
]

PARAM_LABELS = {
    "resilience": "レジリエンス・ハート",
    "empathy":    "共感キャパシティ",
    "passion":    "ラブ・パッション",
    "commit":     "コミット・プロテクト",
    "romance":    "ロマン・探求度",
}

# レーダーチャート下のスコア一覧に添える、専門用語を使わない一言解説
PARAM_DESCRIPTIONS = {
    "resilience": "感情の波にどれだけ強く、揺らいでも立ち直れるか",
    "empathy":    "相手の気持ちに寄り添い、共感できるか",
    "passion":    "恋愛に対する積極性・情熱の強さ",
    "commit":     "一途さや誠実さ、関係を大事に守ろうとする姿勢",
    "romance":    "新しい体験や刺激を求める好奇心の強さ",
}

# SNSシェア時に付与するハッシュタグ。
# 「性格理論＋愛着理論」という本アプリの根拠が伝わりつつ、堅くなりすぎないものを選定。
# 変更したい場合はここを書き換えるだけでOK（他のテキストは自動で追従）。
SHARE_HASHTAG = "ホンネ恋愛診断"


# 5大パラメータ x (高い/低い) = 10種類の「恋愛守護パートナー」キャラクター。
# key: (パラメータキー, "high" or "low")
CHARACTERS = {
    ("resilience", "high"): {
        "name": "アニマ",
        "title": "ニコニコ太陽系聖職者",
        "desc": "どんなに荒れた海も一瞬で凪にする、圧倒的な包容力とメンタルの持ち主。",
        "file": "01_anima_resilience_high.png",
    },
    ("resilience", "low"): {
        "name": "ウプル",
        "title": "雨雲をかぶったガラスの妖精",
        "desc": "傷つきやすく繊細。でも相手の痛みや変化に誰よりも敏感に気づける。",
        "file": "02_upuru_resilience_low.png",
    },
    ("empathy", "high"): {
        "name": "メルティ",
        "title": "とろけるマシュマロロップイヤー",
        "desc": "相手の感情にどこまでも寄り添い、一体化する。話を聞くのが大好きな癒やし系。",
        "file": "03_meruty_empathy_high.png",
    },
    ("empathy", "low"): {
        "name": "キグナス",
        "title": "孤高の氷山ペンギン",
        "desc": "馴れ合わず、常に客観的でクール。感情に流されない的確なアドバイスをくれる。",
        "file": "04_cygnus_empathy_low.png",
    },
    ("passion", "high"): {
        "name": "イグニス",
        "title": "お祭り騒ぎのブースタードラゴン",
        "desc": "好きになったら一直線。エネルギー全開で相手を巻き込む熱血派。",
        "file": "05_ignis_passion_high.png",
    },
    ("passion", "low"): {
        "name": "シリウス",
        "title": "静寂を見守る天体望遠鏡キャット",
        "desc": "自分からぐいぐい行かないが、陰からそっと見守り、深く長く愛を育む。",
        "file": "06_sirius_passion_low.png",
    },
    ("commit", "high"): {
        "name": "イージス",
        "title": "生真面目なファンタジー騎士",
        "desc": "浮気の「う」の字も知らない、圧倒的な誠実さと一途さの塊。約束は絶対守る。",
        "file": "07_aegis_commit_high.png",
    },
    ("commit", "low"): {
        "name": "リベロ",
        "title": "自由気ままなそよ風キャット",
        "desc": "束縛を嫌い、お互いに自由な距離感を保ちたい「来る者拒まず去る者追わず」タイプ。",
        "file": "08_libero_commit_low.png",
    },
    ("romance", "high"): {
        "name": "アストロ",
        "title": "宇宙をめざす天体冒険家",
        "desc": "常に「面白いデート」「見たことない景色」を求める、退屈とは無縁の開拓者。",
        "file": "09_astro_romance_high.png",
    },
    ("romance", "low"): {
        "name": "アルク",
        "title": "居心地のいいこたつコアラ",
        "desc": "変化や冒険よりも、「いつも通り」「定番の安心感」を愛する安定志向の極み。",
        "file": "10_arc_romance_low.png",
    },
}

CHARACTER_MEDIAN = 55  # このスコアを基準に「高い/低い」を判定


def determine_character(scores: dict) -> dict:
    """
    5大パラメータの中で中央値(55点)から最も離れているものを「個性が強い項目」とし、
    対応するキャラクターを返す。
    """
    param = max(scores, key=lambda k: abs(scores[k] - CHARACTER_MEDIAN))
    level = "high" if scores[param] >= CHARACTER_MEDIAN else "low"
    character = dict(CHARACTERS[(param, level)])  # コピーして返す
    character["param"] = param
    character["level"] = level
    return character


def compute_scores(answers: dict, dating: str) -> dict:
    """
    answers: {1: 1〜5, 2: 1〜5, ..., 16: 1〜5} の dict (int)
    dating : "0" / "1-2" / "3+"
    戻り値: 5大パラメータ (10〜100点)
    """
    a = answers

    # ① 因子ベース得点（各2〜10点）
    e_stabil  = (6 - a[4])  + a[9]
    agree     = (6 - a[2])  + a[7]
    extra     = a[1]        + (6 - a[6])
    consc     = a[3]        + (6 - a[8])
    open_     = a[5]        + (6 - a[10])
    a_anxiety = a[11] + a[12]
    a_avoid   = a[13] + a[14]
    a_secure  = a[15] + a[16]

    # ② Q17による動的分配
    if dating == "0":
        resilience = ((e_stabil * 0.80) + (a_secure * 0.20)) * 10
        empathy    = ((agree    * 0.80) + ((12 - a_avoid) * 0.20)) * 10
        passion    = ((extra    * 0.80) + ((12 - a_avoid) * 0.20)) * 10
        commit     = ((consc    * 0.80) + ((12 - a_anxiety) * 0.20)) * 10
        romance    = ((open_    * 0.85) + (extra * 0.15)) * 10
    elif dating == "1-2":
        resilience = ((e_stabil * 0.60) + (a_secure * 0.40)) * 10
        empathy    = ((agree    * 0.70) + ((12 - a_avoid) * 0.30)) * 10
        passion    = ((extra    * 0.70) + ((12 - a_avoid) * 0.30)) * 10
        commit     = ((consc    * 0.70) + ((12 - a_anxiety) * 0.30)) * 10
        romance    = ((open_    * 0.80) + (extra * 0.20)) * 10
    else:  # "3+"
        resilience = ((e_stabil * 0.40) + (a_secure * 0.60)) * 10
        empathy    = ((agree    * 0.40) + ((12 - a_avoid) * 0.60)) * 10
        passion    = ((extra    * 0.40) + ((12 - a_avoid) * 0.60)) * 10
        commit     = ((consc    * 0.40) + ((12 - a_anxiety) * 0.60)) * 10
        romance    = ((open_    * 0.70) + (extra * 0.30)) * 10

    return {
        "resilience": round(resilience, 1),
        "empathy":    round(empathy, 1),
        "passion":    round(passion, 1),
        "commit":     round(commit, 1),
        "romance":    round(romance, 1),
    }


def compute_match(a_scores: dict, b_scores: dict) -> dict:
    """
    仕様書セクション5のマッチングアルゴリズム。
    a_scores / b_scores は compute_scores() の戻り値と同じ形式の dict。
    """
    # ① 価値観の類似性スコア（最大40点）
    diff_roman  = abs(a_scores["romance"] - b_scores["romance"])
    diff_commit = abs(a_scores["commit"]  - b_scores["commit"])
    score_roman  = max(0, 20 - (diff_roman * 0.22))
    score_commit = max(0, 20 - (diff_commit * 0.22))
    similarity_score = score_roman + score_commit

    # ② 社交の相補性スコア（最大30点）
    diff_passion = abs(a_scores["passion"] - b_scores["passion"])
    if diff_passion <= 15 or (40 <= diff_passion <= 70):
        complementary_score = 30
    else:
        complementary_score = 15

    # ③ 安全ネットスコア（最大30点）
    min_r = min(a_scores["resilience"], b_scores["resilience"])
    max_r = max(a_scores["resilience"], b_scores["resilience"])
    if (min_r <= 40 and max_r >= 80) or (min_r > 40):
        safety_score = 30
    else:
        safety_score = 10

    total = similarity_score + complementary_score + safety_score

    return {
        "total": round(total, 1),
        "similarity_score": round(similarity_score, 1),
        "complementary_score": complementary_score,
        "safety_score": safety_score,
    }
