import requests
from bs4 import BeautifulSoup
import os
import json
from datetime import datetime
import time
import re

# --- 1. 카카오 토큰 갱신 ---
def get_access_token():
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": os.environ.get("KAKAO_CLIENT_ID"),
        "refresh_token": os.environ.get("KAKAO_REFRESH_TOKEN")
    }
    response = requests.post(url, data=data).json()
    return response.get("access_token")

# --- 2. 데이터 크롤링 및 HTML 파일 생성 ---
def save_qt_to_html():
    headers = {'User-Agent' : 'Mozilla/5.0'}
    res = requests.get('https://sum.su.or.kr:8888/bible/today', headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')

    # 기본 정보 추출
    main_title = soup.select_one('#bible_text').text.strip()
    full_title = soup.select_one('#bibleinfo_box_3').text.strip()
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # [성경 본문 추출]
    bible_text = ""
    verses = soup.select('#body_list > li')
    for v in verses:
        num = v.select_one('.num').text.strip()
        info = v.select_one('.info').text.strip()
        bible_text += f"<b>{num}절</b> {info}<br>"
    
    # [해설 및 기도 가공]
    exp_box = soup.select_one('#body_cont_3')
    processed_text = ""
    if exp_box:
        raw_text = exp_box.get_text("\n", strip=True)
        
        # 핵심 질문 강조
        processed_text = raw_text.replace("하나님은 어떤 분입니까?", "<h3>✨ 하나님은 어떤 분입니까?</h3>")
        processed_text = processed_text.replace("내게 주시는 교훈은 무엇입니까?", "<h3>📝 내게 주시는 교훈은 무엇입니까?</h3>")
        
        # 절 구분 강조 (1절, 2-5절 등)
        processed_text = re.sub(r'(\d+-\d+절|\d+절)', r'<br><br><b>📍 \1</b><br>', processed_text)
        
        # 기도 섹션 및 세부 제목
        processed_text = processed_text.replace("기도", "<br><hr><h3>🙏 오늘의 기도</h3>")
        processed_text = processed_text.replace("공동체-", "<br><b>🔹 공동체</b><br>")
        processed_text = processed_text.replace("열방-", "<br><b>🔹 열방</b><br>")
        
        # 일반 줄바꿈 처리
        processed_text = processed_text.replace("\n", "<br>")

    # --- HTML 스타일 및 구조 정의 (다크모드 대응) ---
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>오늘의 QT: {main_title}</title>
        <style>
            :root {{ color-scheme: light dark; }}
            body {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                line-height: 1.8;
                font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", sans-serif;
                background-color: #ffffff;
                color: #1f2328;
            }}
            h1 {{ font-size: 1.5rem; border-bottom: 2px solid #eaecef; padding-bottom: 10px; }}
            h3 {{ color: #0969da; margin-top: 30px; margin-bottom: 10px; }}
            blockquote {{
                background: #f6f8fa;
                border-left: 5px solid #d0d7de;
                margin: 20px 0;
                padding: 10px 20px;
                color: #57606a;
            }}
            hr {{ border: 0; border-top: 1px solid #d0d7de; margin: 30px 0; }}
            b {{ color: #cf222e; }}

            /* 다크모드 전용 스타일 */
            @media (prefers-color-scheme: dark) {{
                body {{ background-color: #0d1117; color: #c9d1d9; }}
                h1 {{ border-bottom-color: #30363d; }}
                h3 {{ color: #58a6ff; }}
                blockquote {{ background: #161b22; border-left-color: #30363d; color: #8b949e; }}
                hr {{ border-top-color: #30363d; }}
                b {{ color: #ffa657; }}
            }}
        </style>
    </head>
    <body>
        <h1>📖 오늘의 QT: {main_title}</h1>
        <blockquote>
            <strong>날짜:</strong> {date_str}<br>
            <strong>본문:</strong> {full_title}
        </blockquote>
        
        <h3>📜 성경 본문</h3>
        <div>{bible_text}</div>
        
        <hr>
        {processed_text}
        
        <footer style="margin-top: 50px; font-size: 0.8rem; color: gray; text-align: center;">
            본 내용은 매일 성경 크롤링을 통해 제공됩니다.
        </footer>
    </body>
    </html>
    """

    if not os.path.exists('data'): os.makedirs('data')
    filename = "data/today_qt.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    return main_title, filename

# --- 3. 카카오톡 전송 ---
def send_kakao(token, title, file_path):
    user_id = "qazwsx5381"
    repo_name = "QT_BOT"
    
    # 캐시 방지를 위해 타임스탬프 추가
    timestamp = int(time.time())
    github_link = f"https://{user_id}.github.io/{repo_name}/{file_path}?v={timestamp}"
    homepage_link = "https://sum.su.or.kr:8888/bible/today"

    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {token}"}
    
    post_data = {
        "template_object": json.dumps({
            "object_type": "text",
            "text": f"📢 오늘의 QT: {title}\n\n말씀과 해설 전문은 아래 버튼을 눌러 확인하세요!",
            "link": {"web_url": github_link, "mobile_web_url": github_link},
            "buttons": [
                {
                    "title": "📄 텍스트로 보기",
                    "link": {"web_url": github_link, "mobile_web_url": github_link}
                },
                {
                    "title": "🌐 공식 홈페이지",
                    "link": {"web_url": homepage_link, "mobile_web_url": homepage_link}
                }
            ]
        })
    }
    requests.post(url, headers=headers, data=post_data)

# --- 메인 실행 ---
if __name__ == "__main__":
    try:
        access_token = get_access_token()
        qt_title, path = save_qt_to_html()
        send_kakao(access_token, qt_title, path)
        print(f"성공: {qt_title} 전송 완료")
    except Exception as e:
        print(f"에러 발생: {e}")
