import os
import sys
import uuid
import yt_dlp
from apify_client import ApifyClient
from dotenv import load_dotenv

# [긴급 수정] 강제로 진짜 라이브러리 로드 시도
try:
    import youtube_transcript_api
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
except ImportError:
    # 혹시 설치가 안 됐을 경우를 대비
    YouTubeTranscriptApi = None

load_dotenv()

def get_youtube_data(url):
    """
    유튜브 영상의 자막(Transcript)을 텍스트로 가져옵니다.
    """
    if YouTubeTranscriptApi is None:
        return None, "youtube-transcript-api 라이브러리가 설치되지 않았습니다."

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

        # [안전 장치] 한국어 -> 영어 -> 자동생성 순으로 시도
        try:
            # 1. 수동 자막 (한국어/영어)
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        except (NoTranscriptFound, Exception):
            # 2. 자동 생성 자막이라도 가져오기
            try:
                transcript_list_all = YouTubeTranscriptApi.list_transcripts(video_id)
                # 한국어나 영어가 있으면 가져오고, 없으면 그냥 첫 번째(자동) 거 가져오기
                transcript = transcript_list_all.find_generated_transcript(['ko', 'en'])
                transcript_list = transcript.fetch()
            except Exception:
                 # 진짜 아무것도 없으면 에러
                 return None, "자막을 찾을 수 없습니다. (자동 자막도 없음)"

        text_data = " ".join([t['text'] for t in transcript_list])
        return text_data, None

    except TranscriptsDisabled:
        return None, "이 영상은 자막 기능이 꺼져 있습니다."
    except Exception as e:
        return None, f"자막 읽기 에러: {str(e)}"

# --- (아래 함수들은 기존과 동일합니다. 그대로 두세요) ---
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
        if os.path.exists(filename): return filename, None
        return None, "파일 생성 실패"
    except Exception as e:
        if os.path.exists(filename): os.remove(filename)
        return None, "다운로드 실패"
