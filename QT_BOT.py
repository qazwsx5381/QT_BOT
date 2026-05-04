import requests
from bs4 import BeautifulSoup
import os
import json
import time

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

# --- 2. 데이터 크롤링 및 텍스트 생성 ---
def get_qt_content():
    headers = {'User-Agent' : 'Mozilla/5.0'}
    data = requests.get('https://sum.su.or.kr:8888/bible/today', headers=headers)
    soup = BeautifulSoup(data.text, 'html.parser')

    main_title = soup.select_one('#bible_text').text.strip()
    full_title = soup.select_one('#bibleinfo_box_3').text.strip()
    
    # 파일에 담을 전체 내용 구성
    content = f"📖 제목: {main_title}\n📍 본문: {full_title}\n"
    content += "="*50 + "\n\n[ 성경 본문 ]\n"
    
    verses = soup.select('#body_list > li')
    for verse in verses:
        num = verse.select_one('.num').text.strip()
        info = verse.select_one('.info').text.strip()
        content += f"{num} | {info}\n"
    
    content += "\n" + "="*50 + "\n\n[ 본문 해설 및 기도 ]\n"
    explanation_box = soup.select_one('#body_cont_3')
    if explanation_box:
        content += explanation_box.get_text("\n", strip=True)

    return main_title, content

# --- 3. 파일 업로드 및 카톡 전송 ---
def send_kakao_file(token, title, content):
    filename = "today_qt.txt"
    
    # 1) 임시 텍스트 파일 생성
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    # 2) 카카오 서버에 파일 업로드 (스크랩 전송 방식)
    # 나에게 보내기 API는 직접 파일 첨부가 까다로우므로, 
    # 가장 안정적인 '텍스트 메시지' 전송을 유지하되 파일 내용을 함께 보냅니다.
    # 만약 파일 자체를 전송하려면 '카카오톡 채널' 권한이 필요하므로 
    # 개인용으로는 아래처럼 '요약본 + 전체보기 링크' 형식이 가장 좋습니다.

    send_url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {token}"}
    
    # 카톡 창에는 요약만 보여주고, 파일은 로그 확인용으로 남깁니다.
    summary = f"📢 오늘의 QT: {title}\n\n전체 내용은 아래 '전체보기' 또는 웹사이트를 확인하세요."
    
    post_data = {
        "template_object": json.dumps({
            "object_type": "text",
            "text": summary,
            "link": {"web_url": "https://sum.su.or.kr:8888/bible/today"},
            "button_title": "웹에서 전체보기"
        })
    }
    
    res = requests.post(send_url, headers=headers, data=post_data)
    return res.status_code

# --- 실행 ---
access_token = get_access_token()
qt_title, qt_full_content = get_qt_content()
status = send_kakao_file(access_token, qt_title, qt_full_content)

print(f"전송 결과: {status}")
