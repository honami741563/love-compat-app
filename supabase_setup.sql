-- Supabaseの SQL Editor で実行してください
create table if not exists results (
    hash_id     text primary key,
    nickname    text not null,
    answers     jsonb not null,
    scores      jsonb not null,
    dating      text not null,
    created_at  timestamptz not null default now()
);

-- 補足: このアプリはSupabaseの「anon/authenticatedキー」経由ではなく、
-- サーバー(Flask)からPostgres接続文字列で直接つなぐ方式のため、
-- RLS(行レベルセキュリティ)は必須ではありません。
-- 「hash_idが一致する1件のみ取得する」というアクセス制御は
-- 引き続きアプリ側(db.py)のクエリで担保しています。
