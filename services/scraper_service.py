import os
import uuid
import requests
from apify_client import ApifyClient
from dotenv import load_dotenv
from bs4 import BeautifulSoup
# [확실하게 변경] yt_dlp 버리고 pytubefix 사용
from pytubefix import YouTube 

load_dotenv()

def get_video_file(url):
    """
    URL을 받아 영상 파일(mp4)을 다운로드하고 경로를 반환
    (유튜브: pytubefix OAuth TV인증 / 인스타: Apify)
    """
    file_path = f"video_{uuid.uuid4()}.mp4"
    
    # [1] 인스타그램
    if "instagram.com" in url:
        try:
            apify_token = os.getenv("APIFY_API_TOKEN")
            if not apify_token: return None, "APIFY_API_TOKEN 없음"
            
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
            return None, "인스타 영상 링크 실패"
        except Exception as e:
            return None, f"인스타 에러: {str(e)}"

    # [2] 유튜브 (Pytubefix - TV 인증 모드)
    else:
        try:
            print(f"📺 Pytubefix(TV모드)로 다운로드 시도: {url}")
            
            # use_oauth=True, allow_oauth_cache=True 필수!
            # 아까 터미널에서 만든 tokens.json을 자동으로 읽어서 인증함
            yt = YouTube(url, use_oauth=True, allow_oauth_cache=True)
            
            # 쇼츠/일반 영상 모두 대응하기 위해 스트림 검색 로직 강화
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            
            if not stream:
                # progressive(영상+음성 합본)가 없으면 영상만이라도 가져오기 (쇼츠 대비)
                stream = yt.streams.filter(file_extension='mp4').order_by('resolution').desc().first()

            if stream:
                stream.download(filename=file_path)
                
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    return file_path, None
                
            return None, "다운로드 실패 (영상 스트림을 찾을 수 없습니다.)"
            
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            
            error_msg = str(e)
            # 인증 토큰 문제일 경우 안내 메시지 출력
            if "device" in error_msg or "code" in error_msg:
                return None, "🚨 인증 토큰 만료! 터미널에서 'python3 -c ...' 명령어로 다시 인증해주세요."
            
            return None, f"유튜브 에러: {error_msg}"

def get_naver_blog_content(url):
    """네이버 블로그 (기존 유지)"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36"}
        if "blog.naver.com" in url and "m.blog.naver.com" not in url:
            url = url.replace("blog.naver.com", "m.blog.naver.com")

        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        content_div = soup.find('div', class_='se-main-container')
        if not content_div: content_div = soup.find('div', class_='post_ct')
        return content_div.get_text(strip=True) if content_div else "본문 없음"
    except Exception as e:
        return f"블로그 에러: {str(e)}"
