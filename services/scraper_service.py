import os
import uuid
import yt_dlp
import sys
# [수정] 충돌 방지를 위해 모듈 전체를 임포트
import youtube_transcript_api
from youtube_transcript_api import YouTubeTranscriptApi

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

def get_youtube_data(url):
    """
    유튜브 영상의 자막(Transcript)을 텍스트로 가져옵니다.
    """
    try:
        video_id = ""
        if "youtu.be" in url:
            video_id = url.split("/")[-1].split("?")[0]
        elif "watch?v=" in url:
            video_id = url.split("watch?v=")[1].split("&")[0]
        elif "shorts" in url:
            video_id = url.split("shorts/")[1].split("?")[0]
        
        if not video_id: return None, "영상 ID 없음"

        # [수정] 호출 방식 변경 (클래스 직접 호출)
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        except Exception:
            # 자동 생성 자막 시도
            try:
                transcript_list_all = YouTubeTranscriptApi.list_transcripts(video_id)
                transcript = transcript_list_all.find_generated_transcript(['ko', 'en'])
                transcript_list = transcript.fetch()
            except:
                return None, "자막을 찾을 수 없습니다."

        text_data = " ".join([t['text'] for t in transcript_list])
        return text_data, None

    except Exception as e:
        return None, f"자막 에러: {str(e)}"

# --- 인스타그램은 기존과 동일 ---
def get_instagram_data(url):
    try:
        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token: return None, "APIFY_API_TOKEN 없음"
        client = ApifyClient(apify_token)
        run = client.actor("apify/instagram-scraper").call(run_input={"urls": [url]})
        dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
        if dataset_items:
            item = dataset_items[0]
            return item.get("caption", "") or item.get("firstComment", ""), None
        return None, "데이터 없음"
    except Exception as e: return None, str(e)

def download_video(url):
    """
    유튜브 영상 다운로드 (실패 시 안전하게 처리)
    """
    filename = f"video_{uuid.uuid4()}.mp4"
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': filename,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'match_filter': yt_dlp.utils.match_filter_func("duration < 600"), 
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        # [중요] 파일이 존재하고, 크기가 0보다 커야 성공
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            return filename, None
        else:
            # 빈 파일이면 삭제
            if os.path.exists(filename): os.remove(filename)
            return None, "다운로드 실패 (빈 파일)"
            
    except Exception as e:
        if os.path.exists(filename): os.remove(filename)
        return None, "다운로드 에러 (IP 차단됨)"
