# -*- coding: utf-8 -*-
"""
DB層。

環境変数 DATABASE_URL が設定されていれば Supabase(PostgreSQL) を、
設定されていなければ SQLite (app.db) を使う。
→ ローカル開発時はこれまで通りネット接続不要で動作し、
   本番(Render)ではSupabaseに接続してデータを永続化する。

呼び出し側(app.py)から見た関数のインターフェースは変更していないため、
app.py側の修正は不要。
"""
import os
import json
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL")
BACKEND = "postgres" if DATABASE_URL else "sqlite"

if BACKEND == "postgres":
    import psycopg2
    import psycopg2.extras
else:
    import sqlite3
    DB_PATH = os.path.join(os.path.dirname(__file__), "app.db")


def get_conn():
    if BACKEND == "postgres":
        # SupabaseはSSL接続を前提としているため明示しておく
        return psycopg2.connect(DATABASE_URL, sslmode="require")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    if BACKEND == "postgres":
        cur.execute("""
            CREATE TABLE IF NOT EXISTS results (
                hash_id     TEXT PRIMARY KEY,
                nickname    TEXT NOT NULL,
                answers     JSONB NOT NULL,
                scores      JSONB NOT NULL,
                dating      TEXT NOT NULL,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS results (
                hash_id     TEXT PRIMARY KEY,
                nickname    TEXT NOT NULL,
                answers     TEXT NOT NULL,
                scores      TEXT NOT NULL,
                dating      TEXT NOT NULL,
                created_at  TEXT NOT NULL
            )
        """)
    conn.commit()
    cur.close()
    conn.close()


def save_result(hash_id: str, nickname: str, answers: dict, scores: dict, dating: str):
    conn = get_conn()
    cur = conn.cursor()
    if BACKEND == "postgres":
        cur.execute(
            "INSERT INTO results (hash_id, nickname, answers, scores, dating) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                hash_id,
                nickname,
                psycopg2.extras.Json(answers),
                psycopg2.extras.Json(scores),
                dating,
            ),
        )
    else:
        cur.execute(
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
    cur.close()
    conn.close()


def get_result_by_hash(hash_id: str):
    """ハッシュIDが一致する1件のみを取得（全件取得は行わない）"""
    conn = get_conn()
    cur = conn.cursor()
    if BACKEND == "postgres":
        cur.execute(
            "SELECT hash_id, nickname, answers, scores, dating, created_at "
            "FROM results WHERE hash_id = %s",
            (hash_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row is None:
            return None
        # answers/scoresはJSONB列なのでpsycopg2が自動でdictにしてくれる
        return {
            "hash_id": row[0],
            "nickname": row[1],
            "answers": row[2],
            "scores": row[3],
            "dating": row[4],
            "created_at": row[5].isoformat() if row[5] else None,
        }
    else:
        cur.execute(
            "SELECT hash_id, nickname, answers, scores, dating, created_at "
            "FROM results WHERE hash_id = ?",
            (hash_id,),
        )
        row = cur.fetchone()
        cur.close()
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
    cur = conn.cursor()
    cur.execute("SELECT answers, scores, dating, created_at FROM results")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        header = [f"Q{i}" for i in range(1, 17)] + [
            "dating", "resilience", "empathy", "passion", "commit", "romance", "created_at"
        ]
        writer.writerow(header)
        for row in rows:
            if BACKEND == "postgres":
                answers, scores, dating, created_at = row[0], row[1], row[2], row[3]
                created_at = created_at.isoformat() if created_at else None
            else:
                answers = json.loads(row["answers"])
                scores = json.loads(row["scores"])
                dating = row["dating"]
                created_at = row["created_at"]

            line = [answers.get(str(i), answers.get(i)) for i in range(1, 17)]
            line += [
                dating,
                scores["resilience"], scores["empathy"], scores["passion"],
                scores["commit"], scores["romance"], created_at,
            ]
            writer.writerow(line)
