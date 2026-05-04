import requests
from bs4 import BeautifulSoup
import os
import json
from datetime import datetime

# --- 1. 카카오 토큰 갱신 (기존과 동일) ---
def get_access_token():
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": os.environ.get("KAKAO_CLIENT_ID"),
        "refresh_token": os.environ.get("KAKAO_REFRESH_TOKEN")
    }
    response = requests.post(url, data=data).json()
    return response.get("access_token")

# --- 2. 데이터 크롤링 및 파일 저장 ---
def save_qt_to_file():
    headers = {'User-Agent' : 'Mozilla/5.0'}
    res = requests.get('https://sum.su.or.kr:8888/bible/today', headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')

    main_title = soup.select_one('#bible_text').text.strip()
    full_title = soup.select_one('#bibleinfo_box_3').text.strip()
    
    # 텍스트 파일 내용 구성
    date_str = datetime.now().strftime("%Y-%m-%d")
    content = f"날짜: {date_str}\n제목: {main_title}\n범위: {full_title}\n\n"
    
    # 본문 추가
    verses = soup.select('#body_list > li')
    for v in verses:
        content += f"{v.select_one('.num').text} {v.select_one('.info').text}\n"
    
    # 해설 추가
    content += "\n[해설 및 기도]\n"
    exp = soup.select_one('#body_cont_3')
    if exp:
        content += exp.get_text("\n", strip=True)

    # 'data' 폴더에 날짜별로 저장 (폴더가 없으면 미리 생성 필요)
    if not os.path.exists('data'): os.makedirs('data')
    filename = f"data/QT_{date_str}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    
    return main_title, filename

# --- 3. 카톡 전송 (GitHub 링크 포함) ---
def send_kakao(token, title, file_path):
    # 1. GitHub 파일 링크 (본인 정보로 수정 필수)
    user_id = "qazwsx5381"
    repo_name = "QT_BOT"
    github_link = f"https://github.com/{user_id}/{repo_name}/blob/main/{file_path}"
    
    # 2. 홈페이지 주소
    homepage_link = "https://sum.su.or.kr:8888/bible/today"

    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {token}"}
    
    # 버튼(buttons) 리스트를 2개로 구성합니다.
    post_data = {
        "template_object": json.dumps({
            "object_type": "text",
            "text": f"📖 오늘의 QT: {title}\n\n전체 내용은 아래 '텍스트 파일' 혹은 '홈페이지 연결' 버튼을 눌러 확인하세요!",
            "link": {
                "web_url": homepage_link,
                "mobile_web_url": homepage_link
            },
            "buttons": [
                {
                    "title": "📄 텍스트 파일로 보기",
                    "link": {
                        "web_url": github_link,
                        "mobile_web_url": github_link
                    }
                },
                {
                    "title": "🌐 홈페이지 연결",
                    "link": {
                        "web_url": homepage_link,
                        "mobile_web_url": homepage_link
                    }
                }
            ]
        })
    }
    
    res = requests.post(url, headers=headers, data=post_data)
    print(f"전송 결과: {res.status_code}")

# 실행
token = get_access_token()
title, file_path = save_qt_to_file()
send_kakao(token, title, file_path)
