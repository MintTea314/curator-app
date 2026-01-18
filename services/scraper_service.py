import os
import sys
# 충돌 방지: 모듈 전체 임포트
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

        # 자막 가져오기 (한국어 -> 영어 -> 자동생성 순서)
        transcript_list = None
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        except:
            try:
                # 자동 생성 자막이라도 긁어오기
                listing = YouTubeTranscriptApi.list_transcripts(video_id)
                # 우선순위: 한국어 자동 -> 영어 자동 -> 아무거나
                try:
                    transcript = listing.find_generated_transcript(['ko'])
                except:
                    try:
                        transcript = listing.find_generated_transcript(['en'])
                    except:
                        transcript = listing.find_transcript(['ko', 'en']) # 수동이라도 다시 시도
                
                transcript_list = transcript.fetch()
            except:
                return None, "이 영상은 자막(음성 텍스트)을 추출할 수 없습니다."

        if not transcript_list:
             return None, "자막 데이터가 비어있습니다."

        text_data = " ".join([t['text'] for t in transcript_list])
        return text_data, None

    except Exception as e:
        return None, f"자막 에러: {str(e)}"

# 인스타그램은 그대로 유지
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
