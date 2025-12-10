from flask import Flask, request, render_template_string
import requests
import difflib

app = Flask(__name__)

GOOGLE_API_KEY = "AIzaSyCye5tUgesxDOqqCKQLZl2ocecyeHnHrNU"
TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"

HTML_PAGE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>가게 번역 도우미</title>
</head>
<body>
  <h1>가게 번역 도우미 (시제품)</h1>
  <form method="POST">
    <label>손님 언어:</label>
    <select name="source_lang">
      <option value="en">English</option>
      <option value="ja">日本語</option>
      <option value="zh">中文</option>
      <option value="ko">한국어</option>
    </select>
    <br><br>
    <label>질문을 입력해주세요:</label><br>
    <textarea name="text" rows="4" cols="40"></textarea>
    <br><br>
    <button type="submit">답변 보기</button>
  </form>

  {% if original_text %}
    <hr>
    <h2>결과</h2>
    <p><b>손님 질문:</b> {{ original_text }}</p>
    <p><b>답변:</b> {{ answer_in_source }}</p>
  {% endif %}
</body>
</html>
"""

def translate_text(text, source, target):
    if not text:
        return ""

    # ✅ source를 아예 보내지 않고, Google이 자동으로 언어 감지하게 만듭니다
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
        print("번역 API 오류 응답:", data)  # Render 로그에서 확인용
        return "(번역 오류가 발생했습니다.)"

QA_DATA = {
  "where is the toilet?": "화장실은 가게 밖으로 나가셔서 오른쪽으로 가시면 있습니다. 비밀번호는 7624입니다.",
  "do you have wifi?": "와이파이는 무료이며, 아이디는 CAFE123이고 비밀번호는 12345678입니다.",
  "is there any peanut in this dish?": "이 음식에는 땅콩이 들어가지 않았습니다. 알레르기 걱정 없이 드셔도 됩니다.",
  "what time do you close?": "저희 매장은 오늘 밤 10시에 마감합니다.",
  "can i take out?": "네, 포장 가능합니다. 원하시는 메뉴를 말씀해 주세요."
}
QA_KEYS = list(QA_DATA.keys())

def find_best_answer(english_question: str, cutoff: float = 0.6):
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

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        source_lang = request.form.get("source_lang", "en")
        raw_text = request.form.get("text", "")

        # ✅ 모든 언어를 무조건 영어로 통일해서 비교
        if source_lang == "en":
            english_for_match = raw_text
        else:
            english_for_match = translate_text(raw_text, source_lang, "en")

        # ✅ 영어 기준으로 가장 비슷한 질문 찾기
        answer_ko = find_best_answer(english_for_match, cutoff=0.6)

        if answer_ko is None:
            answer_ko = "죄송하지만 아직 이 질문에 대한 준비된 답변이 없습니다. 직원에게 직접 문의 부탁드립니다."

        # ✅ 한국어 답변을 다시 손님 언어로 번역
        answer_in_source = translate_text(answer_ko, "ko", source_lang)

        return render_template_string(
            HTML_PAGE,
            original_text=raw_text,
            answer_in_source=answer_in_source,
        )

    return render_template_string(HTML_PAGE)

if __name__ == "__main__":

  app.run(host="0.0.0.0", port=5000)

