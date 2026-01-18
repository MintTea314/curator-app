import os
import uuid
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

def get_youtube_data(url):
    """
    (기존 기능) 유튜브 영상의 자막(Transcript)을 텍스트로 가져옵니다.
    """
    try:
        video_id = ""
        if "youtu.be" in url:
            video_id = url.split("/")[-1].split("?")[0]
        elif "watch?v=" in url:
            video_id = url.split("watch?v=")[1].split("&")[0]
        elif "shorts" in url:
            video_id = url.split("shorts/")[1].split("?")[0]
        
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko'])
        text_data = " ".join([t['text'] for t in transcript_list])
        return text_data, None

    except Exception as e:
        return None, f"자막을 가져올 수 없습니다: {str(e)}"

def get_instagram_data(url):
    """
    (기존 기능) 인스타그램 릴스/게시물 데이터를 가져옵니다.
    """
    try:
        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token:
            return None, "APIFY_API_TOKEN이 없습니다."

        client = ApifyClient(apify_token)
        run_input = {"urls": [url]}
        
        # Apify Actor 실행 (instagram-scraper)
        run = client.actor("apify/instagram-scraper").call(run_input=run_input)
        
        dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
        if dataset_items:
            item = dataset_items[0]
            text = item.get("caption", "") or item.get("firstComment", "")
            return text, None
        return None, "데이터를 찾을 수 없습니다."
        
    except Exception as e:
        return None, f"인스타그램 수집 실패: {str(e)}"

def download_video(url):
    """
    (새로운 기능) 유튜브 영상을 MP4 파일로 다운로드합니다.
    """
    # 임시 파일명 생성 (겹치지 않게 랜덤 이름 사용)
    filename = f"video_{uuid.uuid4()}.mp4"
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best', # 화질 적당히, mp4 형식 우선
        'outtmpl': filename,
        'quiet': True,
        'no_warnings': True,
        # 10분(600초) 넘는 영상은 다운로드 안 함 (서버 용량 보호)
        'match_filter': yt_dlp.utils.match_filter_func("duration < 600"), 
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        if os.path.exists(filename):
            return filename, None
        else:
            return None, "다운로드 실패: 파일이 생성되지 않았습니다."
            
    except Exception as e:
        # 실패 시 혹시 생긴 쓰레기 파일 삭제
        if os.path.exists(filename):
            os.remove(filename)
        return None, f"다운로드 에러: {str(e)}"
