# -*- coding: utf-8 -*-
"""
DB層。まずは SQLite で実装（仕様書ではSupabase/Firestoreを推奨しているが、
ローカル開発しやすいようSQLiteから開始 → 将来Supabaseへ移行しやすい形にしてある）。

RLS相当のルールはアプリ側で担保:
 - 「ハッシュIDが一致する1件だけ取得」を徹底し、全件SELECTのエンドポイントは作らない
"""
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "app.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS results (
            hash_id     TEXT PRIMARY KEY,
            nickname    TEXT NOT NULL,
            answers     TEXT NOT NULL,   -- JSON文字列 (Q1〜Q17の回答)
            scores      TEXT NOT NULL,   -- JSON文字列 (5大パラメータ)
            dating      TEXT NOT NULL,
            created_at  TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_result(hash_id: str, nickname: str, answers: dict, scores: dict, dating: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO results (hash_id, nickname, answers, scores, dating, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            hash_id,
            nickname,
            json.dumps(answers, ensure_ascii=False),
            json.dumps(scores, ensure_ascii=False),
            dating,
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def get_result_by_hash(hash_id: str):
    """ハッシュIDが一致する1件のみを取得（全件取得は行わない）"""
    conn = get_conn()
    row = conn.execute(
        "SELECT hash_id, nickname, answers, scores, dating, created_at "
        "FROM results WHERE hash_id = ?",
        (hash_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "hash_id": row["hash_id"],
        "nickname": row["nickname"],
        "answers": json.loads(row["answers"]),
        "scores": json.loads(row["scores"]),
        "dating": row["dating"],
        "created_at": row["created_at"],
    }


def export_anonymized_csv(path: str):
    """
    将来のデータ譲渡用: ニックネーム・ハッシュIDを除外した匿名化CSVを出力。
    回答値 + 算出スコア + 作成日時 のみ。
    """
    import csv
    conn = get_conn()
    rows = conn.execute("SELECT answers, scores, dating, created_at FROM results").fetchall()
    conn.close()

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        header = [f"Q{i}" for i in range(1, 17)] + [
            "dating", "resilience", "empathy", "passion", "commit", "romance", "created_at"
        ]
        writer.writerow(header)
        for row in rows:
            answers = json.loads(row["answers"])
            scores = json.loads(row["scores"])
            line = [answers.get(str(i), answers.get(i)) for i in range(1, 17)]
            line += [
                row["dating"],
                scores["resilience"], scores["empathy"], scores["passion"],
                scores["commit"], scores["romance"], row["created_at"],
            ]
            writer.writerow(line)
