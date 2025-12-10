from flask import Flask, request, render_template_string
import requests
import difflib
import json

app = Flask(__name__)

# 🔑 여기에 본인 Google Cloud Translation API 키 넣으세요
GOOGLE_API_KEY = "AIzaSyCye5tUgesxDOqqCKQLZl2ocecyeHnHrNU"
TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"

# -----------------------------
# 1. 언어별 UI 문구 정의
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
        "menu_image_title": "Menu image"
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
        "menu_image_title": "メニュー画像"
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
        "menu_image_title": "菜单图片"
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
        "menu_image_title": "메뉴판 이미지"
    },
}

# -----------------------------
# 2. HTML 템플릿 (UI 문구는 texts에서 가져옴)
# -----------------------------
HTML_PAGE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{{ texts.title }}</title>
</head>
<body>
  <h1>{{ texts.heading }}</h1>
  <form method="POST">
    <label>{{ texts.label_guest_lang }}</label>
    <select name="source_lang">
      <option value="en" {% if current_lang == 'en' %}selected{% endif %}>English</option>
      <option value="ja" {% if current_lang == 'ja' %}selected{% endif %}>日本語</option>
      <option value="zh" {% if current_lang == 'zh' %}selected{% endif %}>中文</option>
      <option value="ko" {% if current_lang == 'ko' %}selected{% endif %}>한국어</option>
    </select>
    <br><br>
    <label>{{ texts.label_question }}</label><br>
    <textarea name="text" rows="4" cols="40"></textarea>
    <br><br>
    <button type="submit">{{ texts.button_submit }}</button>
  </form>

  {% if original_text %}
    <hr>
    <h2>{{ texts.result_title }}</h2>
    <p><b>{{ texts.result_question }}</b> {{ original_text }}</p>
    <p><b>{{ texts.result_answer }}</b> {{ answer_in_source }}</p>
  {% endif %}

  {% if menu_image %}
    <hr>
    <h2>{{ texts.menu_image_title }}</h2>
    <img src="{{ menu_image }}" alt="Menu image" style="max-width: 100%; height: auto;">
  {% endif %}
</body>
</html>
"""

# -----------------------------
# 3. Google 번역 함수 (언어 자동 감지)
# -----------------------------
def translate_text(text, source, target):
    if not text:
        return ""

    # 👉 source는 보내지 않고, Google에 자동 감지를 맡깁니다.
    params = {
        "key": GOOGLE_API_KEY,
        "q": text,
        "target": target,
        "format": "text",
    }

    resp = requests.post(TRANSLATE_URL, params=params)
    data = resp.json()

    try:
        return data["data"]["translations"][0]["translatedText"]
    except Exception:
        print("번역 API 오류 응답:", data)
        return "(번역 오류가 발생했습니다.)"

# -----------------------------
# 4. 미리 등록해 둔 Q&A (영어 질문 → 한국어 답변)
# -----------------------------
def load_qa_data(path: str = "qa_data.json"):
    """
    qa_data.json 파일에서 질문/답변 데이터를 읽어옵니다.
    형식은 {"영어 질문": "한국어 답변"} 딕셔너리라고 가정합니다.
    """
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"[경고] {path} 파일을 찾을 수 없습니다. 빈 데이터로 시작합니다.")
        return {}
    except Exception as e:
        print(f"[경고] {path} 파일 읽기 오류: {e}")
        return {}

QA_DATA = load_qa_data()
QA_KEYS = list(QA_DATA.keys())

def find_best_answer(english_question: str, cutoff: float = 0.6):
    """영어 질문과 가장 비슷한 등록 질문을 찾아, 유사도가 cutoff 이상이면 한국어 답변을 반환"""
    if not english_question:
        return None
    normalized = english_question.strip().lower()
    if not normalized:
        return None

    matches = difflib.get_close_matches(normalized, QA_KEYS, n=1, cutoff=cutoff)
    if matches:
        key = matches[0]
        return QA_DATA[key]
    return None

def get_menu_image_for_lang(lang: str):
    mapping = {
        "en": "/static/menu_en.jpg",
        "zh": "/static/menu_zh.jpg",
        "ja": "/static/menu_ja.jpg",
        "ko": "/static/menu_ko.jpg",
    }
    return mapping.get(lang)


# -----------------------------
# 5. 메인 라우트
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # 손님 언어 (UI에서 선택한 값)
        source_lang = request.form.get("source_lang", "en")
        raw_text = (request.form.get("text") or "").strip()

        texts = UI_TEXTS.get(source_lang, UI_TEXTS["en"])
        menu_image = get_menu_image_for_lang(source_lang)

        # 질문이 비어 있으면 그냥 화면만 다시 보여주기
        if not raw_text:
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
            detected_lang, text_in_en = translate_text(raw_text, "en")
        except Exception:
            detected_lang, text_in_en = "auto", raw_text

        # 2) 가장 비슷한 질문/답변 찾기
        best_q, best_answer_ko = find_best_answer(text_in_en)

        if best_answer_ko is None:
            answer_in_source = "(준비된 답변이 없습니다.)"
        else:
            # 3) 한국어 답변을 손님 언어로 다시 번역
            try:
                _, answer_in_source = translate_text(best_answer_ko, source_lang)
            except Exception:
                # 번역 실패하면 한국어 원문이라도 보여주기
                answer_in_source = best_answer_ko

        return render_template_string(
            HTML_PAGE,
            original_text=raw_text,
            answer_in_source=answer_in_source,
            texts=texts,
            current_lang=source_lang,
            menu_image=menu_image,
        )

    # GET 요청 (첫 접속 화면)
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
# 6. 로컬 실행용 (Render에서는 gunicorn app:app 사용)
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)



