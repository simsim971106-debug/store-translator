from flask import Flask, request, render_template_string
import requests
import difflib

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
QA_DATA = {
    "where is the toilet?": "화장실은 가게 밖으로 나가셔서 오른쪽으로 가시면 있습니다. 비밀번호는 7624입니다.",
    "do you have wifi?": "와이파이는 무료이며, 아이디는 CAFE123이고 비밀번호는 12345678입니다.",
    "is there any peanut in this dish?": "이 음식에는 땅콩이 들어가지 않았습니다. 알레르기 걱정 없이 드셔도 됩니다.",
    "what time do you close?": "저희 매장은 오늘 밤 10시에 마감합니다.",
    "can i take out?": "네, 포장 가능합니다. 원하시는 메뉴를 말씀해 주세요.",
}
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

# -----------------------------
# 5. 메인 라우트
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        source_lang = request.form.get("source_lang", "en")
        raw_text = request.form.get("text", "")

        # 1) 손님 질문을 영어로 통일 (이미 영어면 그대로)
        if source_lang == "en":
            english_for_match = raw_text
        else:
            english_for_match = translate_text(raw_text, source_lang, "en")

        # 2) 비슷한 질문 찾기
        answer_ko = find_best_answer(english_for_match, cutoff=0.6)
        if answer_ko is None:
            answer_ko = "죄송하지만 아직 이 질문에 대한 준비된 답변이 없습니다. 직원에게 직접 문의 부탁드립니다."

        # 3) 한국어 답변을 손님 언어로 번역
        answer_in_source = translate_text(answer_ko, "ko", source_lang)

        # 4) UI 문구도 손님이 선택한 언어에 맞추기
        texts = UI_TEXTS.get(source_lang, UI_TEXTS["en"])

        return render_template_string(
            HTML_PAGE,
            original_text=raw_text,
            answer_in_source=answer_in_source,
            texts=texts,
            current_lang=source_lang,
        )

    # GET 요청일 때: 기본 언어는 영어 UI
    default_lang = "en"
    texts = UI_TEXTS[default_lang]
    return render_template_string(
        HTML_PAGE,
        original_text=None,
        answer_in_source=None,
        texts=texts,
        current_lang=default_lang,
    )

# -----------------------------
# 6. 로컬 실행용 (Render에서는 gunicorn app:app 사용)
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
