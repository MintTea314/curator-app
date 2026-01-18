import os
import uuid
import yt_dlp
# [수정 1] 라이브러리 충돌 방지를 위해 import 방식 변경
import youtube_transcript_api
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

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
        
        if not video_id:
            return None, "영상 ID를 찾을 수 없습니다."

        # [수정 2] 한국어(ko) 우선, 없으면 영어(en), 그것도 없으면 자동생성 포함 모든 자막 시도
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        except NoTranscriptFound:
            # 지정 언어가 없으면 가능한 모든 언어 중 첫 번째 것을 가져옴
            transcript_list_all = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript_list = transcript_list_all.find_generated_transcript(['ko', 'en']).fetch()

        text_data = " ".join([t['text'] for t in transcript_list])
        return text_data, None

    except TranscriptsDisabled:
        return None, "이 영상은 자막이 비활성화되어 있습니다."
    except Exception as e:
        return None, f"자막 수집 실패 ({type(e).__name__}): {str(e)}"

def get_instagram_data(url):
    """
    인스타그램 릴스/게시물 데이터를 가져옵니다.
    """
    try:
        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token:
            return None, "APIFY_API_TOKEN이 없습니다."

        client = ApifyClient(apify_token)
        run_input = {"urls": [url]}
        
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
    유튜브 영상을 MP4 파일로 다운로드합니다.
    """
    filename = f"video_{uuid.uuid4()}.mp4"
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': filename,
        'quiet': True,
        'no_warnings': True,
        # 스트림릿 클라우드 IP 차단 우회를 위한 설정 (가볍게 시도)
        'nocheckcertificate': True,
        'match_filter': yt_dlp.utils.match_filter_func("duration < 600"), 
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        if os.path.exists(filename):
            return filename, None
        else:
            return None, "파일 생성 실패"
            
    except Exception as e:
        if os.path.exists(filename):
            os.remove(filename)
        # 에러 메시지를 너무 길게 출력하지 않음
        return None, "다운로드 실패 (서버 IP 차단 가능성 높음)"
