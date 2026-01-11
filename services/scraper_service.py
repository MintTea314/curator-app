import os
import yt_dlp
from apify_client import ApifyClient
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv

load_dotenv()

def get_youtube_data(video_url):
    """
    유튜브 데이터 추출 (안전 모드)
    """
    print(f"🎬 분석 시작: {video_url}")
    
    combined_text = []
    video_id = None
    
    # 1. yt-dlp로 메타데이터 및 댓글 추출
    try:
        # [수정] 복잡한 필터링 제거하고 기본 설정으로 요청
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'getcomments': True, # 댓글 가져오기 필수
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("⏳ 유튜브 정보(댓글 포함) 다운로드 중...")
            info = ydl.extract_info(video_url, download=False)
            
            # 기본 정보
            title = info.get('title', '제목 없음')
            description = info.get('description', '설명 없음')
            video_id = info.get('id')
            
            print(f"✅ 제목 추출 완료: {title}")
            
            combined_text.append(f"== [영상 제목] ==\n{title}\n")
            combined_text.append(f"== [영상 설명] ==\n{description}\n")
            
            # 댓글 처리 (파이썬에서 리스트 슬라이싱으로 처리)
            comments = info.get('comments', [])
            if comments:
                print(f"✅ 댓글 {len(comments)}개 발견! 상위 10개만 분석합니다.")
                top_comments = []
                # 고정 댓글이나 인기 댓글은 보통 앞쪽에 위치함
                for c in comments[:10]: 
                    author = c.get('author', 'Unknown')
                    text = c.get('text', '')
                    top_comments.append(f"- {author}: {text}")
                
                comments_text = "\n".join(top_comments)
                combined_text.append(f"== [댓글 모음] ==\n{comments_text}\n")
            else:
                print("⚠️ 댓글을 발견하지 못했습니다.")
                combined_text.append("== [댓글] ==\n(댓글 없음)\n")
            
    except Exception as e:
        print(f"❌ yt-dlp 에러: {e}")
        # 에러 나도 자막은 시도하기 위해 ID 수동 추출
        if "v=" in video_url:
            video_id = video_url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in video_url:
            video_id = video_url.split("youtu.be/")[1].split("?")[0]
        elif "shorts/" in video_url:
            video_id = video_url.split("shorts/")[1].split("?")[0]

    # 2. 자막 추출
    if video_id:
        try:
            yt = YouTubeTranscriptApi()
            transcript = yt.fetch(video_id, languages=['ko', 'en'])
            
            # 텍스트 합치기
            script_text = ""
            for item in transcript:
                text = getattr(item, 'text', None) or item.get('text')
                if text:
                    script_text += text + " "
            
            combined_text.append(f"== [영상 자막] ==\n{script_text}")
            print("✅ 자막 추출 완료")
            
        except Exception:
            print("⚠️ 자막을 가져올 수 없습니다.")
            combined_text.append("\n(자막 없음)")

    return "\n".join(combined_text), None

# 인스타그램 코드는 동일
def get_instagram_data(insta_url):
    token = os.getenv("APIFY_API_TOKEN")
    if not token: return None, "Apify 토큰 없음"
    try:
        client = ApifyClient(token)
        run = client.actor("apify/instagram-scraper").call(run_input={
            "directUrls": [insta_url], "resultsType": "details", "searchLimit": 1
        })
        items = client.dataset(run["defaultDatasetId"]).list_items().items
        if items and items[0].get("caption"):
            return items[0].get("caption"), None
        return "[내용 없음]", "비공개/차단됨"
    except Exception as e:
        return None, str(e)