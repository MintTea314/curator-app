import os
import uuid
import requests
from apify_client import ApifyClient
from dotenv import load_dotenv
from bs4 import BeautifulSoup
# [변경] yt_dlp 대신 pytubefix 사용
from pytubefix import YouTube 

load_dotenv()

def get_video_file(url):
    """
    URL을 받아 영상 파일(mp4)을 다운로드하고 경로를 반환
    (유튜브: pytubefix OAuth 인증 / 인스타: Apify)
    """
    # 임시 파일명 생성
    file_path = f"video_{uuid.uuid4()}.mp4"
    
    # [1] 인스타그램 (Apify 사용 - 기존 동일)
    if "instagram.com" in url:
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
            return None, f"인스타 에러: {str(e)}"

    # [2] 유튜브 (Pytubefix - TV 인증 모드)
    else:
        try:
            print(f"📺 Pytubefix(TV모드)로 다운로드 시도: {url}")
            
            # use_oauth=True, allow_oauth_cache=True 옵션이 핵심!
            # 아까 터미널에서 만든 토큰 파일을 자동으로 읽어옵니다.
            yt = YouTube(url, use_oauth=True, allow_oauth_cache=True)
            
            # 가장 해상도 높은 mp4 스트림 선택
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            
            if not stream:
                # 쇼츠의 경우 progressive가 없을 수 있어 다시 검색
                stream = yt.streams.filter(file_extension='mp4').order_by('resolution').desc().first()

            if stream:
                stream.download(filename=file_path)
                
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    return file_path, None
                
            return None, "다운로드 실패 (영상 스트림을 찾을 수 없습니다.)"
            
        except Exception as e:
            # 다운로드 실패 시 파일 삭제
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # 혹시 토큰 만료 에러인지 확인
            error_msg = str(e)
            if "device" in error_msg or "code" in error_msg:
                return None, "인증 토큰 만료! 터미널에서 다시 인증해주세요."
            
            return None, f"유튜브 에러: {error_msg}"

def get_naver_blog_content(url):
    """네이버 블로그 (기존 동일)"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36"}
        if "blog.naver.com" in url and "m.blog.naver.com" not in url:
            url = url.replace("blog.naver.com", "m.blog.naver.com")

        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        content_div = soup.find('div', class_='se-main-container')
        if not content_div: content_div = soup.find('div', class_='post_ct')
            
        return content_div.get_text(strip=True) if content_div else "본문 찾기 실패"
    except Exception as e:
        return f"블로그 에러: {str(e)}"
