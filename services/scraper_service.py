# services/scraper_service.py

import os
import uuid
import yt_dlp
import requests
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

def get_video_file(url):
    """
    URL을 받아 영상 파일(mp4)을 다운로드하고 경로를 반환
    """
    file_path = f"video_{uuid.uuid4()}.mp4"
    
    # [1] 인스타그램
    if "instagram.com" in url:
        # ... (기존 인스타 코드 동일) ...
        try:
            apify_token = os.getenv("APIFY_API_TOKEN")
            if not apify_token: return None, "APIFY 토큰 없음"
            
            client = ApifyClient(apify_token)
            run = client.actor("apify/instagram-reel-scraper").call(run_input={"urls": [url]})
            dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
            
            video_url = dataset_items[0].get("videoUrl") if dataset_items else None
            
            if video_url:
                with requests.get(video_url, stream=True) as r:
                    r.raise_for_status()
                    with open(file_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                return file_path, None
            return None, "인스타 링크 찾기 실패"
        except Exception as e:
            return None, f"인스타 에러: {e}"

    # [2] 유튜브 (쿠키 적용 버전)
    else:
        # 쿠키 파일이 있는지 확인
        cookie_file = 'cookies.txt'
        has_cookies = os.path.exists(cookie_file)
        
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': file_path,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'geo_bypass': True,
            # [핵심] 쿠키 파일 사용 설정
            'cookiefile': cookie_file if has_cookies else None,
            # 차단 방지를 위한 헤더 조작
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        try:
            print(f"🍪 쿠키 파일 사용 여부: {has_cookies}") # 로그 확인용
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                return file_path, None
            else:
                return None, "다운로드 실패 (쿠키를 갱신해보거나 로컬에서 시도해보세요)"
        except Exception as e:
            return None, f"유튜브 에러: {str(e)}"
