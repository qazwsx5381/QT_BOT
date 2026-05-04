import requests
from bs4 import BeautifulSoup
import re
import os
import json
import time

# --- 1. 카카오 토큰 갱신 함수 ---
def get_access_token():
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": os.environ.get("KAKAO_CLIENT_ID"),
        "refresh_token": os.environ.get("KAKAO_REFRESH_TOKEN")
    }
    response = requests.post(url, data=data).json()
    return response.get("access_token")

# --- 2. 데이터 크롤링 및 파싱 함수 ---
def get_qt_data():
    headers = {'User-Agent' : 'Mozilla/5.0'}
    data = requests.get('https://sum.su.or.kr:8888/bible/today', headers=headers)
    soup = BeautifulSoup(data.text, 'html.parser')

    # 제목 및 범위
    main_title = soup.select_one('#bible_text').text.strip()
    full_title = soup.select_one('#bibleinfo_box_3').text.strip()
    title_range = full_title.split('찬송가')[0].strip() if '찬송가' in full_title else full_title

    # [메시지 1] 성경 본문 구성
    bible_text = f"📖 {main_title}\n📍 {title_range}\n\n"
    verses = soup.select('#body_list > li')
    for verse in verses:
        num = verse.select_one('.num').text.strip()
        info = verse.select_one('.info').text.strip()
        bible_text += f"{num} {info}\n"

    # [메시지 2] 해설 및 기도 구성
    explanation_box = soup.select_one('#body_cont_3')
    exp_text = "💡 본문 해설\n"
    prayer_text = "\n🙏 오늘의 기도\n"
    
    if explanation_box:
        content_divs = explanation_box.find_all('div', recursive=False)
        is_prayer = False
        for div in content_divs:
            text = div.get_text(strip=True)
            if not text: continue
            if "기도" in text and 'g_text' in div.get('class', []):
                is_prayer = True
                continue
            if is_prayer:
                # \n이 포함된 변경 사항을 f-string 밖에서 미리 처리합니다.
                processed_prayer = text.replace('열방-', '\n열방-')
                prayer_text += f"· {processed_prayer}\n"
            else:
                # 여기도 마찬가지로 안전하게 처리
                processed_exp = re.sub(r'(\d+-\d+절|\d+절)', r'\n📌 \1\n', text)
                exp_text += f"{processed_exp}\n"

    return bible_text, exp_text + prayer_text

# --- 3. 메시지 전송 함수 ---
def send_kakao_msg(token, text_content):
    send_url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    target_url = "https://sum.su.or.kr:8888/bible/today"
    headers = {"Authorization": f"Bearer {token}"}
    
    # 텍스트가 너무 길 경우 카카오 제한(약 400자)에 걸릴 수 있으므로 슬라이싱
    if len(text_content) > 400:
        text_content = text_content[:397] + "..."

    post_data = {
        "template_object": json.dumps({
            "object_type": "text",
            "text": text_content,
            "link": {"web_url": target_url, "mobile_web_url": target_url},
            "button_title": "전체보기"
        })
    }
    return requests.post(send_url, headers=headers, data=post_data)

# --- 메인 실행 ---
access_token = get_access_token()
bible_msg, guide_msg = get_qt_data()

# 첫 번째 메시지: 성경 본문
res1 = send_kakao_msg(access_token, bible_msg)
print(f"본문 전송 결과: {res1.status_code}")

# 카카오 API 방어 기제 피하기 위해 2초 대기
time.sleep(2)

# 두 번째 메시지: 해설 및 기도
res2 = send_kakao_msg(access_token, guide_msg)
print(f"해설 전송 결과: {res2.status_code}")
