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

    main_title = soup.select_one('#bible_text').text.strip()
    full_title_raw = soup.select_one('#bibleinfo_box_3').text.strip()
    full_title = full_title_raw.replace("본문 : ", "").strip()
    # '찬송가'라는 글자와 그 뒤에 오는 숫자/공백을 모두 찾아 삭제합니다.
    full_title = re.sub(r'찬송가.*', '', full_title).strip()
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # [성경 본문 추출] - 각 절을 <div>로 감싸 한 줄씩 구분
    # [성경 본문 추출] - 이미지의 '1절 ... 2절 ...' 구조를 한 줄씩 쪼개기
    bible_text = ""
    # 사이트 구조에 따라 .bible_verse 또는 li 태그를 유연하게 잡습니다.
    verses = soup.select('#body_list > li')
    
    if not verses:
        # 혹시 li 구조가 아닐 경우를 대비한 2차 선택자
        verses = soup.select('.bible_verse')

    for v in verses:
        num_tag = v.select_one('.num')
        info_tag = v.select_one('.info')
        
        if num_tag and info_tag:
            num = num_tag.get_text().strip()   # 예: "1"
            info = info_tag.get_text().strip() # 예: "하나님이 야곱에게 이르시되..."
            
            # <div> 태그에 display: block 스타일을 주어 무조건 한 줄을 다 차지하게 합니다.
            # margin-bottom은 절과 절 사이의 간격을 조절합니다.
            bible_text += f'<div class="content-area">'
            bible_text += f'<b style="color: #0969da; margin-right: 8px;">{num}절</b>'
            bible_text += f'<span>{info}</span>'
            bible_text += f'</div>'
    
    # [해설 및 기도 가공]
    exp_box = soup.select_one('#body_cont_3')
    processed_text = ""
    if exp_box:
        raw_text = exp_box.get_text("\n", strip=True)
        
        # 핵심 질문 강조 (글자 크기 키움)
        processed_text = raw_text.replace("하나님은 어떤 분입니까?", '<h4 class="q-title">✨ 하나님은 어떤 분입니까?</h4>')
        processed_text = processed_text.replace("내게 주시는 교훈은 무엇입니까?", '<h4 class="q-title">📝 내게 주시는 교훈은 무엇입니까?</h4>')
        processed_text = re.sub(r'(?m)^기도$', r'<br><hr><h4 class="q-title">🙏 오늘의 기도</h4>', processed_text)
        
        # 절 구분 강조 (📍 아이콘)
        pattern = r'(?<!\()(\d+:\d+-\d+|\d+:\d+|\d+-\d+절|\d+절)(?!\))'
        
        def add_verse_suffix(match):
            verse_num = match.group(1)
            # 이미 '절'이 붙어 있지 않은 경우에만 '절'을 추가하고 📍 스타일 적용
            suffix = "절" if "절" not in verse_num else ""
            return f'<br><div class="verse-point">📍 {verse_num}{suffix}</div>'

        # 문장 중간이 아닌 독립적인 위치의 숫자만 잡기 위해 flags=re.MULTILINE 사용
        processed_text = re.sub(pattern, add_verse_suffix, processed_text, flags=re.MULTILINE)
        
        # 기도 섹션
        processed_text = processed_text.replace("공동체-", '<div class="pray-item"><b>🔹 공동체</b></div>')
        processed_text = processed_text.replace("열방-", '<div class="pray-item"><b>🔹 열방</b></div>')
        
        # 일반 줄바꿈
        processed_text = processed_text.replace("\n", "<br>")
        processed_text = re.sub(r'(<br\s*/?>\s*){2,}', '<br>', processed_text)
        processed_text = processed_text.replace('</h2><br>', '</h2>')
        processed_text = processed_text.replace('</h4><br>', '</h4>')
        processed_text = processed_text.replace('</div><br>', '</div>')
        processed_text = processed_text.replace('</h4><br><div', '</h4><div')

    # --- HTML 스타일 및 구조 정의 ---
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
                line-height: 1.5;
                font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", sans-serif;
                background-color: #ffffff;
                color: #1f2328;
                font-size: 1.05rem;
            }}
            h1 {{ font-size: 1.6rem; border-bottom: 2px solid #eaecef; padding-bottom: 10px; margin-bottom: 20px; }}
            br {{ content: ""; display: block; margin: 5px 0; }}
            
            /* 질문 제목 강조 */
            .q-title {{ 
                font-size: 1.4rem; 
                color: #d11010; 
                margin-top: 20px; 
                margin-bottom: 15px;
                border-left: 5px solid #d11010;
                padding-left: 10px;
            }}
            
            /* 절 구분 강조 */
            .verse-point {{
                font-weight: bold;
                color: #cf222e;
                margin-top: 25px;
                margin-bottom: 5px;
                font-size: 1.1rem;
            }}
            
            .pray-item {{ margin-top: 15px; font-size: 1.1rem; color: #0969da; }}
            
            blockquote {{
                background: #f6f8fa;
                border-left: 5px solid #d0d7de;
                margin: 20px 0;
                padding: 15px 20px;
                color: #57606a;
                font-size: 0.95rem;
            }}
            
            .content-area {{ font-size: 1.15rem; word-break: keep-all; margin: 15px; }} /* 해설 본문 글자 크기 업그레이드 */
            
            hr {{ border: 0; border-top: 1px solid #d0d7de; margin: 20px 0; }}

            /* 다크모드 대응 */
            @media (prefers-color-scheme: dark) {{
                body {{ background-color: #0d1117; color: #c9d1d9; }}
                h1 {{ border-bottom-color: #30363d; }}
                .q-title {{ color: #ff7b72; border-left-color: #ff7b72; }}
                blockquote {{ background: #161b22; border-left-color: #30363d; color: #8b949e; }}
                .verse-point {{ color: #ffa657; }}
                .pray-item {{ color: #58a6ff; }}
                hr {{ border-top-color: #30363d; }}
            }}
        </style>
    </head>
    <body>
        <h1>📖 오늘의 QT: {main_title}</h1>
        <blockquote>
            <strong>날짜 :</strong> {date_str}<br>
            <strong>본문 :</strong> {full_title}
        </blockquote>
        
        <h3 style="color: #666;">📜 성경 본문</h3>
        <div>
            {bible_text}
        </div>
        
        <hr>
        <div class="content-area">
            {processed_text}
        </div>
        
        <footer style="margin-top: 50px; font-size: 0.8rem; color: gray; text-align: center; padding-bottom: 30px;">
            본 내용은 매일 성경 크롤링을 통해 제공됩니다.
        </footer>
    </body>
    </html>
    """

    if not os.path.exists('data'): os.makedirs('data')

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"data/QT_{date_str}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    return main_title, filename

# --- 3. 카카오톡 전송 (함수는 동일하게 유지) ---
def send_kakao(token, title, file_path):
    user_id = "qazwsx5381"
    repo_name = "QT_BOT"
    github_link = f"https://{user_id}.github.io/{repo_name}/{file_path}"
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

if __name__ == "__main__":
    try:
        access_token = get_access_token()
        qt_title, path = save_qt_to_html()
        send_kakao(access_token, qt_title, path)
        print(f"성공: {qt_title} 전송 완료")
    except Exception as e:
        print(f"에러 발생: {e}")
