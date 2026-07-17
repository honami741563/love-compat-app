# -*- coding: utf-8 -*-
"""
SNS(X/Bluesky/LINE)にリンクを貼ったときのプレビュー画像(OGP画像)を生成する。
Chart.jsはブラウザのJSでしか描画できずSNSのクローラーには見えないため、
サーバー側でmatplotlib+Pillowを使って静的なPNGを都度生成し、ファイルにキャッシュする。
"""
import os
import io
import matplotlib
matplotlib.use("Agg")  # サーバー環境でウィンドウなしで描画するため
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(__file__)
CACHE_DIR = os.path.join(BASE_DIR, "static", "og_cache")
CHAR_DIR = os.path.join(BASE_DIR, "static", "characters")
FONT_PATH = os.path.join(BASE_DIR, "static", "fonts", "NotoSansJP-Variable.ttf")

os.makedirs(CACHE_DIR, exist_ok=True)

CANVAS_SIZE = (1200, 630)
PINK = (255, 99, 150)
PINK_LIGHT = (255, 227, 236)
TEXT_COLOR = (58, 46, 53)


def _font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


def _draw_background(canvas_size=CANVAS_SIZE):
    img = Image.new("RGB", canvas_size, (255, 249, 251))
    draw = ImageDraw.Draw(img)
    # 上から下へのやわらかいピンクのグラデーション
    w, h = canvas_size
    for y in range(h):
        t = y / h
        r = int(255 * (1 - t) + 255 * t)
        g = int(249 * (1 - t) + 227 * t)
        b = int(251 * (1 - t) + 236 * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def _radar_chart_image(scores: dict, labels: dict, color=PINK, size_px=520):
    """1人分のレーダーチャートを透過PNG(PIL Image)として返す"""
    keys = list(labels.keys())
    values = [scores[k] for k in keys] + [scores[keys[0]]]
    angles = np.linspace(0, 2 * np.pi, len(keys), endpoint=False).tolist()
    angles += angles[:1]

    fig = plt.figure(figsize=(size_px / 100, size_px / 100), dpi=100)
    ax = fig.add_subplot(111, polar=True)
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    ax.plot(angles, values, color="#%02x%02x%02x" % color, linewidth=3)
    ax.fill(angles, values, color="#%02x%02x%02x" % color, alpha=0.28)
    ax.set_ylim(0, 100)
    ax.set_yticklabels([])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([labels[k] for k in keys], fontproperties=_fm(), fontsize=13, color="#3a2e35")
    ax.spines['polar'].set_color("#e8b9c8")
    ax.grid(color="#e8b9c8", alpha=0.6)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGBA")


def _radar_chart_image_dual(scores_a, scores_b, labels, size_px=560):
    """2人分を重ね合わせたレーダーチャート"""
    keys = list(labels.keys())
    va = [scores_a[k] for k in keys] + [scores_a[keys[0]]]
    vb = [scores_b[k] for k in keys] + [scores_b[keys[0]]]
    angles = np.linspace(0, 2 * np.pi, len(keys), endpoint=False).tolist()
    angles += angles[:1]

    fig = plt.figure(figsize=(size_px / 100, size_px / 100), dpi=100)
    ax = fig.add_subplot(111, polar=True)
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    ax.plot(angles, va, color="#ff6396", linewidth=3)
    ax.fill(angles, va, color="#ff6396", alpha=0.22)
    ax.plot(angles, vb, color="#4f8dfd", linewidth=3)
    ax.fill(angles, vb, color="#4f8dfd", alpha=0.22)

    ax.set_ylim(0, 100)
    ax.set_yticklabels([])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([labels[k] for k in keys], fontproperties=_fm(), fontsize=13, color="#3a2e35")
    ax.spines['polar'].set_color("#e8b9c8")
    ax.grid(color="#e8b9c8", alpha=0.6)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGBA")


_FM_CACHE = None


def _fm():
    """matplotlibに日本語フォントを認識させる"""
    global _FM_CACHE
    if _FM_CACHE is None:
        from matplotlib import font_manager
        _FM_CACHE = font_manager.FontProperties(fname=FONT_PATH)
    return _FM_CACHE


def _paste_character(canvas, char_file, box, opacity=255):
    char_path = os.path.join(CHAR_DIR, char_file)
    char_img = Image.open(char_path).convert("RGBA")
    char_img.thumbnail((box[2] - box[0], box[3] - box[1]), Image.LANCZOS)
    if opacity < 255:
        alpha = char_img.split()[3].point(lambda p: int(p * opacity / 255))
        char_img.putalpha(alpha)
    x = box[0] + (box[2] - box[0] - char_img.width) // 2
    y = box[1] + (box[3] - box[1] - char_img.height) // 2
    canvas.paste(char_img, (x, y), char_img)


def build_result_image(hash_id: str, data: dict, character: dict, labels: dict) -> str:
    """個人結果ページ用のOGP画像を生成(キャッシュがあればそれを返す)"""
    out_path = os.path.join(CACHE_DIR, f"result_{hash_id}.png")
    if os.path.exists(out_path):
        return out_path

    canvas = _draw_background()
    draw = ImageDraw.Draw(canvas)

    # 左側にキャラクター(大きめ・薄い透過)
    _paste_character(canvas, character["file"], box=(20, 60, 480, 560), opacity=235)

    # 右側にレーダーチャート
    chart = _radar_chart_image(data["scores"], labels)
    canvas.paste(chart, (500, 40), chart)

    # タイトルテキスト
    title_font = _font(46)
    sub_font = _font(30)
    draw.text((40, 20), f"{data['nickname']}さんの恋愛タイプ", font=title_font, fill=TEXT_COLOR)
    draw.text((40, 560), f"恋愛守護パートナーは「{character['name']}」タイプ", font=sub_font, fill=PINK)

    canvas.convert("RGB").save(out_path, "PNG", optimize=True)
    return out_path


def build_match_image(hash_a, hash_b, data_a, data_b, char_a, char_b, match_result, labels) -> str:
    """相性診断(2人)結果ページ用のOGP画像を生成"""
    key = "_".join(sorted([hash_a, hash_b]))
    out_path = os.path.join(CACHE_DIR, f"match_{key}.png")
    if os.path.exists(out_path):
        return out_path

    canvas = _draw_background()
    draw = ImageDraw.Draw(canvas)

    # 左上・左下にキャラクターを縦に並べる
    _paste_character(canvas, char_a["file"], box=(10, 40, 300, 320), opacity=235)
    _paste_character(canvas, char_b["file"], box=(10, 320, 300, 600), opacity=235)

    # 中央に重ね合わせレーダーチャート
    chart = _radar_chart_image_dual(data_a["scores"], data_b["scores"], labels)
    canvas.paste(chart, (300, 60), chart)

    # 右側に相性度を大きく表示
    percent_font = _font(90)
    label_font = _font(34)
    name_font = _font(26)
    draw.text((900, 40), f"{data_a['nickname']} × {data_b['nickname']}", font=name_font, fill=TEXT_COLOR)
    draw.text((900, 90), "相性度", font=label_font, fill=TEXT_COLOR)
    draw.text((900, 130), f"{match_result['total']}%", font=percent_font, fill=PINK)

    canvas.convert("RGB").save(out_path, "PNG", optimize=True)
    return out_path


def pregenerate_result_image(hash_id: str, data: dict, character: dict, labels: dict):
    """
    診断完了時にあらかじめOGP画像を生成しておく。
    SNSクローラーが最初にアクセスした時点で画像がすでに出来上がっているようにするための処理。
    生成に失敗しても診断フロー自体は止めたくないので、例外は握りつぶしてログのみ出す。
    """
    try:
        build_result_image(hash_id, data, character, labels)
    except Exception as e:  # noqa: BLE001
        print(f"[ogimage] 事前生成に失敗しました(result): {e}")


def pregenerate_match_image(hash_a, hash_b, data_a, data_b, char_a, char_b, match_result, labels):
    try:
        build_match_image(hash_a, hash_b, data_a, data_b, char_a, char_b, match_result, labels)
    except Exception as e:  # noqa: BLE001
        print(f"[ogimage] 事前生成に失敗しました(match): {e}")
