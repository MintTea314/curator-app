import os
import uuid
import yt_dlp
import requests
from apify_client import ApifyClient
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

def get_video_file(url):
    """
    URL을 받아 영상 파일(mp4)을 다운로드하고 경로를 반환
    (유튜브/쇼츠/인스타 릴스 통합 지원)
    """
    # 임시 파일명 생성
    file_path = f"video_{uuid.uuid4()}.mp4"
    
    # [1] 인스타그램 (Apify 사용)
    if "instagram.com" in url:
        try:
            apify_token = os.getenv("APIFY_API_TOKEN")
            if not apify_token:
                return None, "APIFY_API_TOKEN이 .env 파일에 없습니다."
            
            # Apify 클라이언트 시작
            client = ApifyClient(apify_token)
            
            # 인스타 릴스 다운로더 액터 실행
            # (만약 실행이 너무 오래 걸리면 타임아웃 설정을 고려해야 함)
            run = client.actor("apify/instagram-reel-scraper").call(run_input={"urls": [url]})
            
            # 결과 데이터셋 가져오기
            dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
            
            video_url = None
            if dataset_items:
                video_url = dataset_items[0].get("videoUrl")
            
            if video_url:
                # 영상 파일 다운로드
                with requests.get(video_url, stream=True) as r:
                    r.raise_for_status()
                    with open(file_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                return file_path, None
            else:
                return None, "인스타 영상 링크를 추출하지 못했습니다."
        except Exception as e:
            return None, f"인스타 다운로드 에러: {str(e)}"

    # [2] 유튜브 & 쇼츠 (yt-dlp + 안드로이드 우회 모드)
    else:
        # 쿠키 파일이 있는지 확인 (서버의 cookies.txt 사용)
        cookie_file = 'cookies.txt'
        has_cookies = os.path.exists(cookie_file)
        
        ydl_opts = {
            'format': 'best[ext=mp4]/best',  # MP4 포맷 최우선
            'outtmpl': file_path,            # 저장될 파일명
            'quiet': True,                   # 지저분한 로그 숨김
            'no_warnings': True,
            'nocheckcertificate': True,      # SSL 인증서 무시
            'ignoreerrors': True,            # 에러 나도 멈추지 않음
            'geo_bypass': True,              # 국가 제한 우회 시도
            
            # [핵심 1] 쿠키 파일 적용 (있으면 쓰고, 없으면 안 씀)
            'cookiefile': cookie_file if has_cookies else None,
            
            # [핵심 2] 오라클 서버 차단 회피용 (안드로이드 앱인 척 속이기)
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web']
                }
            },
            
            # [핵심 3] 헤더 조작 (모바일 브라우저인 척)
            'user_agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        }
        
        try:
            print(f"🎬 다운로드 시작... (Android 모드, 쿠키: {has_cookies})")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # 파일이 진짜 생겼는지, 용량이 0은 아닌지 확인
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                return file_path, None
            else:
                return None, "다운로드 실패 (차단되었거나 영상 정보를 가져올 수 없습니다. 쿠키를 최신으로 교체해보세요.)"
                
        except Exception as e:
            # 다운로드 실패 시 쓰레기 파일이 남았다면 삭제
            if os.path.exists(file_path):
                os.remove(file_path)
            return None, f"유튜브 에러: {str(e)}"

def get_naver_blog_content(url):
    """
    네이버 블로그 본문 텍스트 추출 (기존 코드 유지)
    """
    try:
        # 모바일 버전으로 접속해야 iframe 없이 본문이 바로 보임
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G960N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36"
        }
        # m.blog.naver.com 으로 변환 시도
        if "blog.naver.com" in url and "m.blog.naver.com" not in url:
            url = url.replace("blog.naver.com", "m.blog.naver.com")

        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 본문 영역 추출 (네이버 모바일 블로그 기준)
        content_div = soup.find('div', class_='se-main-container')
        if not content_div:
            content_div = soup.find('div', class_='post_ct') # 구버전
            
        if content_div:
            return content_div.get_text(strip=True)
        else:
            return "본문을 찾을 수 없습니다. (비공개 글이거나 구조가 다름)"
            
    except Exception as e:
        return f"블로그 크롤링 에러: {str(e)}"
