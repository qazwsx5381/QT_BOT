import requests
from bs4 import BeautifulSoup
import re
import os
import json

# --- 1. 카카오 토큰 갱신 함수 ---
def get_access_token():
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": os.environ.get("KAKAO_CLIENT_ID"),
        "refresh_token": os.environ.get("KAKAO_REFRESH_TOKEN")
    }
    response = requests.post(url, data=data)
    print("토큰 갱신 응답:", response.json()) # 이 로그를 확인하면 에러 이유가 정확히 나옵니다.
    return response.json().get("access_token")

# --- 2. 크롤링 및 데이터 가공 ---
def get_qt_data():
    headers = {'User-Agent' : 'Mozilla/5.0'}
    data = requests.get('https://sum.su.or.kr:8888/bible/today', headers=headers)
    soup = BeautifulSoup(data.text, 'html.parser')

    main_title = soup.select_one('#bible_text').text.strip()
    full_title = soup.select_one('#bibleinfo_box_3').text.strip()
    title_range = full_title.split('찬송가')[0].strip() if '찬송가' in full_title else full_title

    # 카톡 전송용 (본문 위주로 요약 - 글자수 제한 때문)
    output = f"📖 {main_title}\n📍 {title_range}\n\n"
    verses = soup.select('#body_list > li')
    for verse in verses[:10]: # 너무 길면 잘리므로 상위 10절까지만
        num = verse.select_one('.num').text.strip()
        info = verse.select_one('.info').text.strip()
        output += f"{num} {info}\n"
    return output

# --- 3. 메인 실행 ---
token = get_access_token()
content = get_qt_data()

send_url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
headers = {"Authorization": f"Bearer {token}"}
post_data = {
    "template_object": json.dumps({
        "object_type": "text",
        "text": content,
        "link": {"web_url": "https://sum.su.or.kr:8888/bible/today"},
        "button_title": "전체 보기"
    })
}

res = requests.post(send_url, headers=headers, data=post_data)
print("전송 결과:", res.status_code)

res = requests.post(send_url, headers=headers, data=post_data)
print(f"상태 코드: {res.status_code}")
print(f"응답 내용: {res.json()}")
