import os
import uuid
import json
import yt_dlp
import requests
# 충돌 방지: 모듈 전체 임포트
import youtube_transcript_api
from youtube_transcript_api import YouTubeTranscriptApi
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

def get_youtube_data(url):
    """
    1차 시도: youtube_transcript_api (빠름)
    2차 시도: yt-dlp 자막 추출 (강력함, IP 차단 우회 가능성 높음)
    """
    video_id = parse_video_id(url)
    if not video_id: return None, "영상 ID를 찾을 수 없습니다."

    # --- [1차 시도] 가벼운 API 라이브러리 사용 ---
    print("Trying method 1: youtube_transcript_api")
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        text_data = " ".join([t['text'] for t in transcript_list])
        return text_data, None
    except Exception:
        # 자동 생성 자막 재시도
        try:
            transcript_list_all = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcript_list_all.find_generated_transcript(['ko', 'en'])
            text_data = " ".join([t['text'] for t in transcript.fetch()])
            return text_data, None
        except Exception as e:
            print(f"Method 1 failed: {e}")

    # --- [2차 시도] yt-dlp 사용 (뒷문 이용) ---
    print("Trying method 2: yt-dlp (metadata fetch)")
    try:
        ydl_opts = {
            'skip_download': True,      # 영상 다운로드 안 함 (가볍게)
            'writesubtitles': True,     # 자막 요청
            'writeautomaticsub': True,  # 자동 자막도 요청
            'subtitleslangs': ['ko', 'en'], # 한국어/영어
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # 1. 자막(subtitles) 확인
            subs = info.get('subtitles') or info.get('automatic_captions')
            
            if subs:
                # 한국어(ko)나 영어(en) 자막 URL 찾기
                sub_url = None
                for lang in ['ko', 'en', 'ko-orig', 'en-orig']:
                    if lang in subs:
                        # json3 형식이 가장 파싱하기 좋음
                        for fmt in subs[lang]:
                            if fmt.get('ext') == 'json3':
                                sub_url = fmt['url']
                                break
                        if sub_url: break
                
                # 자막 URL 내용을 다운로드해서 텍스트로 변환
                if sub_url:
                    sub_data = requests.get(sub_url).json()
                    # json3 포맷에서 텍스트만 추출
                    full_text = ""
                    for event in sub_data.get('events', []):
                        if 'segs' in event:
                            for seg in event['segs']:
                                full_text += seg.get('utf8', '') + " "
                    return full_text.strip(), None
            
            # 자막도 없다면, 설명(description)이라도 리턴
            if info.get('description'):
                return info.get('description'), None

    except Exception as e:
        print(f"Method 2 failed: {e}")

    return None, "❌ 모든 방법 실패: 자막을 가져올 수 없습니다. (유튜브 서버 차단)"

def parse_video_id(url):
    if "youtu.be" in url:
        return url.split("/")[-1].split("?")[0]
    elif "watch?v=" in url:
        return url.split("watch?v=")[1].split("&")[0]
    elif "shorts" in url:
        return url.split("shorts/")[1].split("?")[0]
    return None

# --- 인스타그램 수집 (기존 동일) ---
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

# --- 영상 다운로드 (기존 동일) ---
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
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            return filename, None
        else:
            if os.path.exists(filename): os.remove(filename)
            return None, "다운로드 실패"
    except Exception as e:
        if os.path.exists(filename): os.remove(filename)
        return None, "다운로드 에러"
