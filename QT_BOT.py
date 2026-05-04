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

# --- 2. 데이터 크롤링 및 마크다운 파일 생성 ---
def save_qt_to_md():
    headers = {'User-Agent' : 'Mozilla/5.0'}
    res = requests.get('https://sum.su.or.kr:8888/bible/today', headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')

    main_title = soup.select_one('#bible_text').text.strip()
    full_title = soup.select_one('#bibleinfo_box_3').text.strip()
    
    # 마크다운 내용 구성 (가독성 업그레이드)
    date_str = datetime.now().strftime("%Y-%m-%d")

    md_content = '<meta name="color-scheme" content="light dark">\n\n'
    
    md_content = f"# 📖 오늘의 QT: {main_title}\n\n"
    md_content += f"> 날짜: {date_str}  \n"
    md_content += f"> {full_title}\n\n"
    md_content += "---\n\n"
    
    # [성경 본문]
    md_content += "### 📜 성경 본문\n"
    verses = soup.select('#body_list > li')
    for v in verses:
        num = v.select_one('.num').text.strip()
        info = v.select_one('.info').text.strip()
        md_content += f"{num}절 {info}\n"
    
    # [해설 및 기도]
    md_content += "\n---\n\n### 💡 본문 해설 및 묵상\n"
    exp_box = soup.select_one('#body_cont_3')
    
    if exp_box:
        # 1. 텍스트 추출
        raw_text = exp_box.get_text("\n", strip=True)
        
        # 2. 핵심 질문 강조 (하나님은 어떤 분 / 내게 주시는 교훈)
        # 질문 앞에 줄바꿈과 이모지, 인용구(>)를 넣어 눈에 확 띄게 만듭니다.
        processed_text = raw_text.replace("하나님은 어떤 분입니까?", "\n\n## ✨ 하나님은 어떤 분입니까?\n")
        processed_text = processed_text.replace("내게 주시는 교훈은 무엇입니까?", "\n\n## 📝 내게 주시는 교훈은 무엇입니까?\n")
        
        # 3. 절 구분 강조 (1절, 2-5절 등)
        # 이미 질문 섹션이 나뉘었으므로, 그 안의 절들을 소제목으로 바꿉니다.
        processed_text = re.sub(r'(\d+-\d+절|\d+절)', r'\n\n#### 📍 \1', processed_text)
        processed_text = processed_text.replace("절", "절\n")
        
        # 4. 기도 섹션 마무리
        processed_text = processed_text.replace("기도", "\n\n---\n### 🙏 오늘의 기도\n")
        # 공동체와 열방 앞에 불렛 포인트(-)와 줄바꿈을 추가하여 가독성을 높입니다.
        processed_text = processed_text.replace("공동체-", "\n\n**🔹 공동체**  \n")
        processed_text = processed_text.replace("열방-", "\n\n**🔹 열방**  \n")

        processed_text = re.sub(r'<[^>]+>', '', processed_text)
        
        md_content += processed_text

    # 폴더 생성 및 저장 (today_qt.md로 고정하여 덮어쓰기)
    if not os.path.exists('data'): os.makedirs('data')
    filename = "data/today_qt.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    return main_title, filename

# --- 3. 카카오톡 전송 (버튼 2개) ---
def send_kakao(token, title, file_path):
    # 본인의 정보로 수정하세요
    user_id = "qazwsx5381"
    repo_name = "QT_BOT"
    
    github_link = f"https://{user_id}.github.io/{repo_name}/data/today_qt.md"
    homepage_link = "https://sum.su.or.kr:8888/bible/today"

    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {token}"}
    
    post_data = {
        "template_object": json.dumps({
            "object_type": "text",
            "text": f"📢 오늘의 QT: {title}\n\n전체 내용은 아래 '텍스트로 보기' 혹은 '홈페이지 연결' 버튼을 눌러 확인하세요!",
            "link": {"web_url": github_link, "mobile_web_url": github_link},
            "buttons": [
                {
                    "title": "📄 텍스트로 보기",
                    "link": {"web_url": github_link, "mobile_web_url": github_link}
                },
                {
                    "title": "🌐 홈페이지 연결",
                    "link": {"web_url": homepage_link, "mobile_web_url": homepage_link}
                }
            ]
        })
    }
    res = requests.post(url, headers=headers, data=post_data)
    print(f"전송 결과: {res.status_code}")

# 실행
access_token = get_access_token()
qt_title, path = save_qt_to_md()
send_kakao(access_token, qt_title, path)
