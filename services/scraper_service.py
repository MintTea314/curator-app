import os
import uuid
import yt_dlp
import requests
import time
from apify_client import ApifyClient
from dotenv import load_dotenv
from bs4 import BeautifulSoup # 기존 텍스트 분석용

load_dotenv()

def get_video_file(url):
    """
    URL을 받아 영상 파일(mp4)을 다운로드하고 경로를 반환
    """
    file_path = f"video_{uuid.uuid4()}.mp4"
    
    # 1. 인스타그램 (Apify 사용)
    if "instagram.com" in url:
        try:
            apify_token = os.getenv("APIFY_API_TOKEN")
            if not apify_token: return None, "APIFY_API_TOKEN이 .env에 없습니다."
            
            client = ApifyClient(apify_token)
            # 인스타 릴스 다운로더 액터 실행
            run = client.actor("apify/instagram-reel-scraper").call(run_input={"urls": [url]})
            
            # 결과에서 영상 URL 추출
            dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
            video_url = None
            if dataset_items:
                video_url = dataset_items[0].get("videoUrl")
            
            if video_url:
                with requests.get(video_url, stream=True) as r:
                    r.raise_for_status()
                    with open(file_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                return file_path, None
            else:
                return None, "인스타 영상 링크를 찾을 수 없습니다."
        except Exception as e:
            return None, f"인스타 다운로드 에러: {str(e)}"

    # 2. 유튜브/쇼츠 (yt-dlp 사용 - 오라클 서버라 잘 될 겁니다!)
    else:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': file_path,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            # 오라클 서버 IP 차단 방지용 옵션들
            'geo_bypass': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                return file_path, None
            else:
                return None, "유튜브 다운로드 실패 (서버 차단 가능성)"
        except Exception as e:
            return None, f"유튜브 에러: {str(e)}"

# --- (아래는 기존 블로그 텍스트 수집용 함수들. 그대로 둡니다.) ---
def get_naver_blog_content(url):
    # ... (기존 코드 유지) ...
    pass
