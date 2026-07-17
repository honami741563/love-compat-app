# -*- coding: utf-8 -*-
import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, abort, send_file
from werkzeug.middleware.proxy_fix import ProxyFix

import db
import scoring
import ogimage

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-this-in-production")

# Renderなどのリバースプロキシ経由では、内部的にはHTTPで中継されるため、
# Flaskが「本当はHTTPSだった」と正しく認識できるようにする。
# これが無いと url_for(..., _external=True) が http://... を生成してしまい、
# SNSのクローラーがog:image等の画像URLを取得できなくなる。
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

db.init_db()


@app.route("/")
def index():
    # シェアURL経由で「診断未経験のまま」訪れた場合、誰との相性を見るために来たかを表示する
    invited_by = None
    target_hash = session.get("match_target")
    if target_hash:
        target = db.get_result_by_hash(target_hash)
        if target:
            invited_by = target["nickname"]

    return render_template(
        "quiz.html",
        questions=scoring.QUESTIONS,
        dating_choices=scoring.DATING_CHOICES,
        invited_by=invited_by,
    )


@app.route("/submit", methods=["POST"])
def submit():
    # Q1〜Q16 を収集
    answers = {}
    try:
        for q in scoring.QUESTIONS:
            val = int(request.form[f"q{q['id']}"])
            if not (1 <= val <= 5):
                raise ValueError
            answers[q["id"]] = val
        dating = request.form["dating"]
        if dating not in ("0", "1-2", "3+"):
            raise ValueError
    except (KeyError, ValueError):
        # 未回答があれば診断画面に戻す
        return redirect(url_for("index"))

    scores = scoring.compute_scores(answers, dating)

    # DB保存前の一時データとしてセッションに保持し、ニックネーム入力画面へ
    session["pending_answers"] = answers
    session["pending_dating"] = dating
    session["pending_scores"] = scores
    return redirect(url_for("nickname"))


@app.route("/nickname", methods=["GET", "POST"])
def nickname():
    if "pending_scores" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        nick = request.form.get("nickname", "").strip()
        if not nick:
            return render_template("nickname.html", error="ニックネームを入力してください")

        hash_id = uuid.uuid4().hex[:12]
        db.save_result(
            hash_id=hash_id,
            nickname=nick,
            answers=session["pending_answers"],
            scores=session["pending_scores"],
            dating=session["pending_dating"],
        )

        # SNSシェア時のプレビュー画像をあらかじめ生成しておく(クローラー訪問時のタイムアウト対策)
        saved_data = db.get_result_by_hash(hash_id)
        character = scoring.determine_character(saved_data["scores"])
        ogimage.pregenerate_result_image(hash_id, saved_data, character, scoring.PARAM_LABELS)

        # 自分のハッシュIDをセッションに保持（相性診断で使用）
        session["my_hash"] = hash_id
        session.pop("pending_answers", None)
        session.pop("pending_dating", None)
        session.pop("pending_scores", None)

        # シェアURL経由（未診断）で来ていた場合は、招待してくれた相手との相性画面へ自動で戻す
        target_hash = session.pop("match_target", None)
        if target_hash:
            return redirect(url_for("match", hash_id=target_hash))

        return redirect(url_for("result", hash_id=hash_id))

    return render_template("nickname.html", error=None)


@app.route("/result/<hash_id>")
def result(hash_id):
    data = db.get_result_by_hash(hash_id)
    if data is None:
        abort(404)

    is_owner = session.get("my_hash") == hash_id
    character = scoring.determine_character(data["scores"])
    og_image_url = url_for("og_image_result", hash_id=hash_id, _external=True)

    return render_template(
        "result.html",
        data=data,
        is_owner=is_owner,
        labels=scoring.PARAM_LABELS,
        descriptions=scoring.PARAM_DESCRIPTIONS,
        character=character,
        og_image_url=og_image_url,
    )


@app.route("/og/result/<hash_id>.png")
def og_image_result(hash_id):
    """SNSシェア時のプレビュー画像(レーダーチャート+キャラクター)"""
    data = db.get_result_by_hash(hash_id)
    if data is None:
        abort(404)
    character = scoring.determine_character(data["scores"])
    path = ogimage.build_result_image(hash_id, data, character, scoring.PARAM_LABELS)
    response = send_file(path, mimetype="image/png")
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response


@app.route("/share/<hash_id>")
def share(hash_id):
    """
    共有専用ページ。
    悪用防止のため、本人（session['my_hash'] == hash_id）以外はアクセスできない。
    """
    data = db.get_result_by_hash(hash_id)
    if data is None:
        abort(404)
    if session.get("my_hash") != hash_id:
        abort(403)

    character = scoring.determine_character(data["scores"])
    view_url = url_for("result", hash_id=hash_id, _external=True)
    match_url = url_for("match", hash_id=hash_id, _external=True)

    return render_template(
        "share.html",
        data=data,
        character=character,
        view_url=view_url,
        match_url=match_url,
        hashtag=scoring.SHARE_HASHTAG,
    )


@app.route("/compare")
def compare_manual():
    """手動モード: 相手のスコアをスライダーで直入力し、フロントでリアルタイム計算"""
    my_hash = session.get("my_hash")
    if not my_hash:
        return redirect(url_for("index"))
    my_data = db.get_result_by_hash(my_hash)
    if my_data is None:
        return redirect(url_for("index"))

    return render_template("compare_manual.html", my_scores=my_data["scores"], labels=scoring.PARAM_LABELS)


@app.route("/compare/save", methods=["POST"])
def compare_save():
    """
    手動入力した相手のスコアを保存し、共有可能な相性結果ページ(match_pair)へ遷移する。
    保存されるのは「入力されたスコアのみ」で、Q1〜16の個別回答は存在しない(dating='manual')。
    """
    my_hash = session.get("my_hash")
    if not my_hash:
        return redirect(url_for("index"))

    try:
        opponent_scores = {}
        for key in scoring.PARAM_LABELS:
            v = float(request.form[key])
            opponent_scores[key] = round(min(100, max(10, v)), 1)
    except (KeyError, ValueError):
        return redirect(url_for("compare_manual"))

    nickname = request.form.get("nickname", "").strip() or "ゲスト"
    hash_id = uuid.uuid4().hex[:12]
    db.save_result(
        hash_id=hash_id,
        nickname=nickname,
        answers={},
        scores=opponent_scores,
        dating="manual",
    )

    # SNSシェア時のプレビュー画像をあらかじめ生成しておく
    my_data = db.get_result_by_hash(my_hash)
    opponent_data = db.get_result_by_hash(hash_id)
    if my_data:
        match_result = scoring.compute_match(my_data["scores"], opponent_data["scores"])
        char_a = scoring.determine_character(my_data["scores"])
        char_b = scoring.determine_character(opponent_data["scores"])
        ogimage.pregenerate_match_image(
            my_hash, hash_id, my_data, opponent_data, char_a, char_b, match_result, scoring.PARAM_LABELS
        )

    return redirect(url_for("match_pair", hash_a=my_hash, hash_b=hash_id))


@app.route("/match/<hash_id>")
def match(hash_id):
    """シェアモード: 他ユーザーのハッシュURL経由でアクセスした場合の入り口"""
    target = db.get_result_by_hash(hash_id)
    if target is None:
        abort(404)

    my_hash = session.get("my_hash")

    if my_hash == hash_id:
        # 自分自身の共有リンクを踏んだ場合は自分の結果画面へ
        return redirect(url_for("result", hash_id=hash_id))

    my_data = db.get_result_by_hash(my_hash) if my_hash else None

    if my_data:
        # すでに診断済み → 二人分の相性結果ページへ（先にOGP画像を仕込んでおく）
        match_result = scoring.compute_match(my_data["scores"], target["scores"])
        char_a = scoring.determine_character(my_data["scores"])
        char_b = scoring.determine_character(target["scores"])
        ogimage.pregenerate_match_image(
            my_data["hash_id"], hash_id, my_data, target, char_a, char_b, match_result, scoring.PARAM_LABELS
        )
        return redirect(url_for("match_pair", hash_a=my_data["hash_id"], hash_b=hash_id))

    # 未診断 → 招待ページ（相手の結果+「自分も診断をやってみる」ボタン）を表示
    session["match_target"] = hash_id
    character = scoring.determine_character(target["scores"])
    og_image_url = url_for("og_image_result", hash_id=hash_id, _external=True)
    return render_template(
        "invite.html",
        target=target,
        character=character,
        labels=scoring.PARAM_LABELS,
        og_image_url=og_image_url,
    )


@app.route("/match/<hash_a>/<hash_b>")
def match_pair(hash_a, hash_b):
    """
    二人分の相性結果ページ（共有可能・状態を持たない）。
    hash_a, hash_bさえ分かれば誰でも再現できるURLなので、そのままシェア用リンクとして使える。
    """
    if hash_a == hash_b:
        abort(404)

    data_a = db.get_result_by_hash(hash_a)
    data_b = db.get_result_by_hash(hash_b)
    if data_a is None or data_b is None:
        abort(404)

    match_result = scoring.compute_match(data_a["scores"], data_b["scores"])
    char_a = scoring.determine_character(data_a["scores"])
    char_b = scoring.determine_character(data_b["scores"])

    my_hash = session.get("my_hash")
    is_participant = my_hash in (hash_a, hash_b)
    share_url = url_for("match_pair", hash_a=hash_a, hash_b=hash_b, _external=True)
    og_image_url = url_for("og_image_match", hash_a=hash_a, hash_b=hash_b, _external=True)

    return render_template(
        "match_pair.html",
        data_a=data_a,
        data_b=data_b,
        char_a=char_a,
        char_b=char_b,
        match_result=match_result,
        labels=scoring.PARAM_LABELS,
        is_participant=is_participant,
        share_url=share_url,
        og_image_url=og_image_url,
        hashtag=scoring.SHARE_HASHTAG,
    )


@app.route("/og/match/<hash_a>/<hash_b>.png")
def og_image_match(hash_a, hash_b):
    data_a = db.get_result_by_hash(hash_a)
    data_b = db.get_result_by_hash(hash_b)
    if data_a is None or data_b is None:
        abort(404)
    match_result = scoring.compute_match(data_a["scores"], data_b["scores"])
    char_a = scoring.determine_character(data_a["scores"])
    char_b = scoring.determine_character(data_b["scores"])
    path = ogimage.build_match_image(
        hash_a, hash_b, data_a, data_b, char_a, char_b, match_result, scoring.PARAM_LABELS
    )
    response = send_file(path, mimetype="image/png")
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response


@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", code=403, message="このページは本人のみアクセスできます。"), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="ページが見つかりませんでした。"), 404


if __name__ == "__main__":
    app.run(debug=True, port=5000)
