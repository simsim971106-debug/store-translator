import os
import json
import difflib
import requests
from flask import Flask, request, render_template_string

app = Flask(__name__)

# -----------------------------
# 1. 구글 번역 API 설정
# -----------------------------
GOOGLE_API_KEY = "AIzaSyACB4g9KPdDMT2JIp0AiLZ1wGXvIhSLohI"

TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"


def translate_text(text: str, target_lang: str) -> tuple[str, str]:
    """
    구글 번역 API를 사용해 text를 target_lang으로 번역합니다.
    (source 언어는 auto로 감지)
    return: (감지된 언어 코드, 번역된 문장)
    """
    if not GOOGLE_API_KEY:
        # API 키가 없으면 그냥 원문을 그대로 돌려줌
        return "auto", text

    params = {
        "key": GOOGLE_API_KEY,
        "q": text,
        "target": target_lang,
        "format": "text",
        "source": "auto",
    }
    resp = requests.post(TRANSLATE_URL, data=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    translations = data["data"]["translations"][0]
    translated_text = translations["translatedText"]
    detected_lang = translations.get("detectedSourceLanguage", "auto")
    return detected_lang, translated_text


# -----------------------------
# 2. qa_data.json 로딩
# -----------------------------
def load_qa_data(path: str = "qa_data.json") -> dict:
    """qa_data.json에서 질문/답변 데이터를 읽어옵니다."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("qa_data.json must contain a JSON object {question: answer}")
        return data
    except FileNotFoundError:
        print("qa_data.json 파일을 찾을 수 없습니다. 빈 데이터로 시작합니다.")
        return {}
    except Exception as e:
        print(f"qa_data.json을 불러오는 중 오류가 발생했습니다: {e}")
        return {}


QA_DATA = load_qa_data()


def find_best_answer(question_en: str) -> tuple[str | None, str | None]:
    """
    영어로 된 질문(question_en)과 qa_data.json의 키들을 비교해서
    가장 비슷한 질문과 그에 해당하는 답변(한국어)을 반환합니다.
    """
    if not QA_DATA:
        return None, None

    # 소문자 변환 후 매칭
    q_norm = question_en.strip().lower()
    candidates = list(QA_DATA.keys())
    norm_map = {k.lower(): k for k in candidates}

    # 가장 비슷한 키 찾기
    best = difflib.get_close_matches(q_norm, norm_map.keys(), n=1)
    if not best:
        return None, None

    best_norm = best[0]
    best_key = norm_map[best_norm]

    # 유사도 점수 체크 (너무 다르면 None)
    score = difflib.SequenceMatcher(None, q_norm, best_norm).ratio()
    if score < 0.45:  # 필요하면 이 값 조정
        return None, None

    return best_key, QA_DATA.get(best_key)


# -----------------------------
# 3. UI 텍스트 (언어별)
# -----------------------------
UI_TEXTS = {
    "en": {
        "title": "Store Translation Helper (Demo)",
        "heading": "Store Translation Helper (Demo)",
        "label_guest_lang": "Customer language:",
        "label_question": "Please enter your question:",
        "button_submit": "Show answer",
        "result_title": "Result",
        "result_question": "Customer question:",
        "result_answer": "Answer:",
        "menu_image_title": "Menu image",
    },
    "ja": {
        "title": "翻訳サポート（デモ）",
        "heading": "翻訳サポート（デモ）",
        "label_guest_lang": "お客様の言語：",
        "label_question": "質問を入力してください：",
        "button_submit": "回答を表示",
        "result_title": "結果",
        "result_question": "お客様の質問：",
        "result_answer": "回答：",
        "menu_image_title": "メニュー画像",
    },
    "zh": {
        "title": "店铺翻译助手（演示）",
        "heading": "店铺翻译助手（演示）",
        "label_guest_lang": "顾客使用的语言：",
        "label_question": "请输入您的问题：",
        "button_submit": "显示回答",
        "result_title": "结果",
        "result_question": "顾客的问题：",
        "result_answer": "回答：",
        "menu_image_title": "菜单图片",
    },
    "ko": {
        "title": "가게 번역 도우미 (시제품)",
        "heading": "가게 번역 도우미 (시제품)",
        "label_guest_lang": "손님 언어:",
        "label_question": "질문을 입력해주세요:",
        "button_submit": "답변 보기",
        "result_title": "결과",
        "result_question": "손님 질문:",
        "result_answer": "답변:",
        "menu_image_title": "메뉴판 이미지",
    },
}


# -----------------------------
# 4. 언어별 메뉴판 이미지 경로
# -----------------------------
def get_menu_image_for_lang(lang: str) -> str | None:
    """
    손님 언어에 따라 static 폴더의 메뉴판 이미지 경로를 반환합니다.
    """
    mapping = {
        "en": "/static/menu_en.jpg",
        "ja": "/static/menu_ja.jpg",
        "zh": "/static/menu_zh.jpg",
        "ko": "/static/menu_ko.jpg",
    }
    return mapping.get(lang)


# -----------------------------
# 5. HTML 템플릿
# -----------------------------
HTML_PAGE = """
<!doctype html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <title>{{ texts.title }}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #f5f5f5;
            margin: 0;
            padding: 0;
        }
        .page {
            max-width: 900px;
            margin: 30px auto;
            padding: 0 16px;
        }
        .card {
            background: #ffffff;
            border-radius: 10px;
            padding: 20px 24px;
            margin-bottom: 16px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        }
        h1 {
            margin: 0 0 10px;
            font-size: 32px;
            color: #222;
        }
        h2 {
            margin-top: 0;
            font-size: 20px;
            color: #333;
        }
        label {
            font-weight: 600;
            color: #444;
        }
        select, textarea, button {
            font-family: inherit;
            font-size: 14px;
        }
        select, textarea {
            border-radius: 6px;
            border: 1px solid #ccc;
            padding: 8px 10px;
            box-sizing: border-box;
        }
        textarea {
            width: 100%;
            min-height: 100px;
            resize: vertical;
            margin-top: 6px;
        }
        button {
            margin-top: 12px;
            padding: 8px 18px;
            border: none;
            border-radius: 999px;
            background: #ff7f50;
            color: #ffffff;
            font-weight: 600;
            cursor: pointer;
        }
        button:hover {
            background: #ff6a33;
        }
        .field-row {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .field-row select {
            width: auto;
            min-width: 160px;
        }
        .menu-image {
            margin-top: 14px;
        }
        .menu-image img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            border: 1px solid #eee;
        }
        .result-label {
            font-weight: 700;
        }
        .result-block p {
            margin: 4px 0 8px;
        }
    </style>
</head>
<body>
<div class="page">

    <!-- 상단: 제목 + 언어 선택 + 메뉴판 이미지 -->
    <div class="card">
        <h1>{{ texts.heading }}</h1>

        <div class="field-row" style="margin-bottom: 8px;">
            <label for="source_lang">{{ texts.label_guest_lang }}</label>
            <!-- 언어만 바꾸는 작은 폼 -->
            <form method="post" id="lang-form">
                <select name="source_lang" id="source_lang"
                        onchange="document.getElementById('lang-form').submit();">
                    <option value="en" {% if current_lang == 'en' %}selected{% endif %}>English</option>
                    <option value="ja" {% if current_lang == 'ja' %}selected{% endif %}>日本語</option>
                    <option value="zh" {% if current_lang == 'zh' %}selected{% endif %}>中文</option>
                    <option value="ko" {% if current_lang == 'ko' %}selected{% endif %}>한국어</option>
                </select>
            </form>
        </div>

        {% if menu_image %}
        <div class="menu-image">
            <h2 style="margin-bottom: 6px;">{{ texts.menu_image_title }}</h2>
            <img src="{{ menu_image }}" alt="Menu image">
        </div>
        {% endif %}
    </div>

    <!-- 질문 입력 카드 -->
    <div class="card">
        <form method="post">
            <!-- 질문 보낼 때도 현재 언어 값을 같이 보냄 -->
            <input type="hidden" name="source_lang" value="{{ current_lang }}">
            <label for="text">{{ texts.label_question }}</label>
            <textarea name="text" id="text">{{ original_text or '' }}</textarea>
            <button type="submit">{{ texts.button_submit }}</button>
        </form>
    </div>

    <!-- 결과 카드 -->
    {% if original_text is not none %}
    <div class="card result-block">
        <h2>{{ texts.result_title }}</h2>
        {% if original_text %}
            <p><span class="result-label">{{ texts.result_question }}</span> {{ original_text }}</p>
            <p><span class="result-label">{{ texts.result_answer }}</span> {{ answer_in_source }}</p>
        {% else %}
            <p>{{ texts.result_question }} (질문이 입력되지 않았습니다.)</p>
        {% endif %}
    </div>
    {% endif %}

</div>
</body>
</html>
"""


# -----------------------------
# 6. 라우팅
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        source_lang = request.form.get("source_lang", "en")
        raw_text = (request.form.get("text") or "").strip()

        texts = UI_TEXTS.get(source_lang, UI_TEXTS["en"])
        menu_image = get_menu_image_for_lang(source_lang)

        # 언어만 바꿔서 다시 로드하는 경우 (질문 없이 submit)
        if "lang-form" in request.form or not raw_text:
            return render_template_string(
                HTML_PAGE,
                original_text="",
                answer_in_source="",
                texts=texts,
                current_lang=source_lang,
                menu_image=menu_image,
            )

        # 1) 손님 질문을 영어로 번역
        try:
            _, text_in_en = translate_text(raw_text, "en")
        except Exception:
            text_in_en = raw_text

        # 2) 가장 비슷한 질문/답변 찾기
        _, best_answer_ko = find_best_answer(text_in_en)

        if best_answer_ko is None:
            answer_in_source = "(준비된 답변이 없습니다.)"
        else:
            # 3) 한국어 답변을 손님 언어로 다시 번역
            try:
                _, answer_in_source = translate_text(best_answer_ko, source_lang)
            except Exception:
                answer_in_source = best_answer_ko

        return render_template_string(
            HTML_PAGE,
            original_text=raw_text,
            answer_in_source=answer_in_source,
            texts=texts,
            current_lang=source_lang,
            menu_image=menu_image,
        )

    # GET: 첫 화면
    default_lang = "en"
    texts = UI_TEXTS[default_lang]
    menu_image = get_menu_image_for_lang(default_lang)

    return render_template_string(
        HTML_PAGE,
        original_text=None,
        answer_in_source=None,
        texts=texts,
        current_lang=default_lang,
        menu_image=menu_image,
    )


# -----------------------------
# 7. 로컬 실행용
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)




