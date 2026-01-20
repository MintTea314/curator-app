import os
import json
import time
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# 선생님이 지정하신 모델명 유지
MODEL_NAME = 'gemini-2.5-pro'

def get_client():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except:
        api_key = os.getenv("GEMINI_API_KEY")
    return genai.Client(api_key=api_key)

def analyze_video(video_path):
    """영상 파일을 분석하여 맛집 정보 추출"""
    client = get_client()

    # 1. 파일 검사
    if not os.path.exists(video_path):
        print(f"❌ [에러] 파일이 없습니다: {video_path}")
        return {"summary": "영상 파일 없음", "places": []}
        
    file_size = os.path.getsize(video_path)
    print(f"📁 영상 파일 확인됨: {video_path} (크기: {file_size/1024/1024:.2f} MB)")
    
    if file_size == 0:
        print(f"❌ [에러] 파일 크기가 0입니다.")
        return {"summary": "다운로드된 영상이 비어있음", "places": []}

    try:
        # 2. 파일 업로드 (방식 변경: 파일을 읽지 않고 경로만 전달)
        print("🚀 [1단계] 구글 서버로 영상 업로드 시작...")
        
        # [수정] f.read()로 읽지 않고 path 파라미터 사용 (서버 충돌 방지)
        upload_result = client.files.upload(path=video_path)
        
        print(f"✅ [1단계 완료] 업로드 성공! (이름: {upload_result.name})")
        
        # 3. 처리 대기
        print("⏳ [2단계] 구글측 영상 처리 대기 중...")
        while True:
            file_meta = client.files.get(name=upload_result.name)
            if file_meta.state == "ACTIVE":
                print("✅ [2단계 완료] 영상 처리 완료! (ACTIVE)")
                break
            elif file_meta.state == "FAILED":
                print("❌ [2단계 실패] 구글 측에서 영상 처리를 실패함.")
                return {"summary": "영상 처리 실패 (Google Side)", "places": []}
            time.sleep(2)

        # 4. 분석 요청
        print(f"🧠 [3단계] AI({MODEL_NAME})에게 분석 요청 중...")
        prompt = """
        이 영상을 분석해서 맛집 정보를 JSON으로 줘.
        
        [미션]
        1. **시각(OCR):** 영상에 나오는 간판, 메뉴판 텍스트를 읽어서 정확한 상호명을 찾아.
        2. **청각(Audio):** 나레이션이나 대화에서 음식 맛 표현이나 특징을 들어.
        3. **위치 추론:** 만약 지역명(예: 성수동, 강남)이 보이면 포함해.
        
        [출력 형식]
        {{
            "summary": "영상 내용 3줄 요약 (분위기, 주요 메뉴, 특징)",
            "places": [
                {{
                    "search_query": "찾아낸 식당 이름 + 지역명 (예: 런던베이글뮤지엄 도산)",
                    "description": "영상에서 본 비주얼과 들은 맛 표현"
                }}
            ]
        }}
        """

        response = client.models.generate_content(
            model=MODEL_NAME, 
            contents=[upload_result, prompt],
            config=types.GenerateContentConfig(response_mime_type='application/json')
        )
        
        print("🎉 [3단계 완료] AI 응답 수신 성공!")
        return json.loads(response.text)

    except Exception as e:
        print(f"💥 [치명적 에러] 분석 도중 터짐: {str(e)}")
        # 혹시 모델명 에러인지 힌트 제공
        if "404" in str(e) or "Not Found" in str(e):
             return {"summary": f"모델명({MODEL_NAME})을 찾을 수 없습니다. (gemini-1.5-pro 로 변경 필요)", "places": []}
        return {"summary": f"시스템 에러: {str(e)}", "places": []}

# --- (아래 analyze_text, summarize_reviews 함수는 기존 유지) ---
def analyze_text(text):
    # (기존 코드와 동일)
    client = get_client()
    # ...
    # 모델명은 MODEL_NAME 변수 사용
    # ...
    pass 

def summarize_reviews(reviews):
    # (기존 코드와 동일)
    pass
