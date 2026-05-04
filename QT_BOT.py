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
    # GitHub 저장소의 파일 직접 보기 주소 구성 (본인 계정/레포명 확인 필수)
    # 예: https://github.com/사용자아이디/레포명/blob/main/data/QT_2026-05-04.txt
    user_id = "본인의_GitHub_아이디"
    repo_name = "본인의_레포지토리_이름"
    github_link = f"https://github.com/{user_id}/{repo_name}/blob/main/{file_path}"

    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {token}"}
    post_data = {
        "template_object": json.dumps({
            "object_type": "text",
            "text": f"📢 오늘의 QT: {title}\n\n전체 해설은 GitHub 파일에서 확인하세요!",
            "link": {"web_url": github_link, "mobile_web_url": github_link},
            "button_title": "텍스트 파일로 보기"
        })
    }
    requests.post(url, headers=headers, data=post_data)

# 실행
token = get_access_token()
title, file_path = save_qt_to_file()
send_kakao(token, title, file_path)
