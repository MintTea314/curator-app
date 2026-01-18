import os
import json
import time
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def get_client():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except:
        api_key = os.getenv("GEMINI_API_KEY")
    return genai.Client(api_key=api_key)

def analyze_video(video_path):
    client = get_client()
    
    print("📤 비디오 업로드 중...")
    # 1. 비디오 파일 업로드
    video_file = client.files.upload(path=video_path)
    
    # 2. 처리 대기 (유튜브처럼 처리 시간이 필요함)
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = client.files.get(name=video_file.name)

    if video_file.state.name == "FAILED":
        return {"summary": "비디오 처리 실패", "places": []}

    print("👀 AI가 영상을 시청 중...")
    # 3. 영상 분석 요청
    prompt = """
    이 영상을 보고 맛집 정보를 정리해줘.
    영상 화면에 나오는 '식당 이름' 글자(Text)와 내레이션 소리를 모두 조합해서 정확한 이름을 찾아내.
    (자막이 틀릴 수 있으니 화면에 적힌 글자를 최우선으로 믿어줘.)

    [필수 답변 형식 (JSON)]
    {
        "summary": "영상 전체 내용 3줄 요약",
        "places": [
            {
                "search_query": "구글 지도 검색용 정확한 식당 이름 (예: 치앙마이 블루누들)",
                "description": "특징 및 가격 정보 한 줄 요약"
            }
        ]
    }
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp', # 동영상 처리는 2.0 Flash가 가장 빠르고 강력함
            contents=[video_file, prompt],
            config=types.GenerateContentConfig(
                response_mime_type='application/json'
            )
        )
        
        # 분석 끝나면 클라우드 파일 삭제 (청소)
        # (SDK 버전에 따라 delete 메서드가 다를 수 있어 try 처리)
        try:
            client.files.delete(name=video_file.name)
        except:
            pass

        if response.text:
            return json.loads(response.text)
        else:
            return {"summary": "AI 응답 없음", "places": []}
            
    except Exception as e:
        return {"summary": f"에러 발생: {str(e)}", "places": []}

# (기존 텍스트 요약 함수도 혹시 모르니 남겨둠)
def summarize_text(text):
    # ... (기존 코드 유지) ...
    pass
