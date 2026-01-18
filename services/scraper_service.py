import os
import uuid
import yt_dlp
from apify_client import ApifyClient
from dotenv import load_dotenv

# [디버깅 & 안전장치] 라이브러리 위치 확인 및 임포트
try:
    import youtube_transcript_api
    # 실제 라이브러리가 어디서 로딩되는지 로그에 찍어봅니다.
    print(f"DEBUG: youtube_transcript_api loaded from: {youtube_transcript_api.__file__}")
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
except (ImportError, AttributeError) as e:
    print(f"DEBUG: Library Import Failed: {e}")
    YouTubeTranscriptApi = None

load_dotenv()

def get_youtube_data(url):
    """
    유튜브 영상의 자막(Transcript)을 텍스트로 가져옵니다.
    """
    if YouTubeTranscriptApi is None:
        return None, "❌ 라이브러리 로드 실패. (로그를 확인하세요)"

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

        # 자막 가져오기
        transcript_list = None
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        except Exception:
            try:
                # 자동 생성 자막 시도
                transcript_list_all = YouTubeTranscriptApi.list_transcripts(video_id)
                transcript = transcript_list_all.find_generated_transcript(['ko', 'en'])
                transcript_list = transcript.fetch()
            except Exception:
                pass

        if not transcript_list:
             return None, "자막을 찾을 수 없습니다."

        text_data = " ".join([t['text'] for t in transcript_list])
        return text_data, None

    except Exception as e:
        return None, f"자막 에러: {str(e)}"

# --- (나머지 함수는 그대로) ---
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
