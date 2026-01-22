import os
import time
import requests
import re
from pytubefix import YouTube
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

# [기존] 유튜브 다운로드 함수
def get_video_file(url):
    """유튜브 영상을 다운로드하여 로컬 파일 경로 반환"""
    try:
        yt = YouTube(url, use_oauth=True, allow_oauth_cache=True)
        print(f"📥 유튜브 다운로드 시작: {yt.title}")
        
        # 쇼츠나 일반 영상 모두 처리
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        if not stream:
            stream = yt.streams.filter(file_extension='mp4').order_by('resolution').desc().first()
            
        out_file = stream.download()
        
        # 파일명 단순화 (오류 방지)
        base, ext = os.path.splitext(out_file)
        new_file = f"video_{int(time.time())}.mp4"
        os.rename(out_file, new_file)
        
        return new_file, None
    except Exception as e:
        return None, f"유튜브 다운로드 에러: {str(e)}"

# [신규] 인스타그램 다운로드 함수 (Apify 사용)
def get_instagram_content(url):
    """
    인스타 링크를 분석하여 콘텐츠(영상 or 이미지들)를 다운로드함
    반환값: (type, paths, error)
    type: 'video' 또는 'image'
    paths: 파일 경로(문자열) 또는 파일 경로 리스트
    """
    api_token = os.getenv("APIFY_API_TOKEN")
    if not api_token:
        return None, None, "Apify API 토큰이 없습니다. .env를 확인해주세요."

    client = ApifyClient(api_token)
    
    print(f"📸 인스타그램 분석 요청 (Apify): {url}")

    # Apify의 'instagram-scraper' 액터 사용
    run_input = {
        "directUrls": [url],
        "resultsType": "details", # 상세 정보 필요
        "searchLimit": 1,
    }

    try:
        # Actor 실행
        run = client.actor("apify/instagram-scraper").call(run_input=run_input)
        
        # 결과 가져오기
        dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
        
        if not dataset_items:
            return None, None, "인스타 게시물을 찾을 수 없습니다. (비공개 계정일 수 있음)"
            
        item = dataset_items[0]
        
        # --- A. 릴스 (영상) 인 경우 ---
        # videoUrl이 존재하면 영상으로 취급
        if item.get("videoUrl"):
            print("🎥 릴스(동영상) 감지됨")
            video_url = item["videoUrl"]
            
            # 영상 다운로드
            res = requests.get(video_url, stream=True)
            filename = f"insta_reel_{int(time.time())}.mp4"
            with open(filename, 'wb') as f:
                for chunk in res.iter_content(chunk_size=1024):
                    f.write(chunk)
            return "video", filename, None

        # --- B. 게시물 (사진) 인 경우 ---
        # images 리스트나 displayUrl 사용
        elif item.get("images") or item.get("displayUrl"):
            print("🖼️ 사진 게시물 감지됨")
            image_urls = item.get("images", [])
            
            # 만약 images 리스트가 비어있으면 썸네일(displayUrl) 하나라도 씀
            if not image_urls and item.get("displayUrl"):
                image_urls = [item["displayUrl"]]
            
            # 최대 5장까지만 다운로드 (AI 토큰 절약)
            saved_files = []
            for i, img_url in enumerate(image_urls[:5]):
                try:
                    res = requests.get(img_url)
                    fname = f"insta_img_{int(time.time())}_{i}.jpg"
                    with open(fname, 'wb') as f:
                        f.write(res.content)
                    saved_files.append(fname)
                except:
                    continue
            
            if not saved_files:
                return None, None, "사진을 다운로드할 수 없습니다."
                
            return "image", saved_files, None
            
        else:
            return None, None, "지원하지 않는 인스타 형식입니다."

    except Exception as e:
        return None, None, f"Apify 에러: {str(e)}"

# [통합] 네이버 블로그 등 텍스트
def get_naver_blog_content(url):
    try:
        if "m.blog.naver.com" not in url:
            url = url.replace("blog.naver.com", "m.blog.naver.com")
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        content = soup.find('div', class_='se-main-container')
        if not content:
            content = soup.find('div', id='viewTypeSelector')
            
        return content.get_text(strip=True) if content else "본문 없음"
    except Exception as e:
        return f"크롤링 실패: {str(e)}"
