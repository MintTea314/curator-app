import os
import json
import time
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# 선생님이 옳았습니다! 2.5 Pro 모델 유지합니다.
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

    if not os.path.exists(video_path):
        return {"summary": "영상 파일 없음", "places": []}
        
    try:
        # [수정] 메모리 충돌 방지 업로드 방식 (file=f)
        with open(video_path, "rb") as f:
            upload_result = client.files.upload(
                file=f, 
                config=types.UploadFileConfig(mime_type='video/mp4')
            )
        
        # 처리 대기
        while True:
            file_meta = client.files.get(name=upload_result.name)
            if file_meta.state == "ACTIVE":
                break
            elif file_meta.state == "FAILED":
                return {"summary": "영상 처리 실패 (Google Side)", "places": []}
            time.sleep(1)

        # 분석 요청
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
        
        return json.loads(response.text)

    except Exception as e:
        return {"summary": f"에러 발생: {str(e)}", "places": []}

def analyze_text(text):
    client = get_client()
    prompt = f"""
    다음 텍스트에서 맛집 정보를 추출해줘. JSON 형식으로.
    텍스트: {text[:20000]} 
    Format: {{ "summary": "요약", "places": [{{"search_query": "식당이름", "description": "특징"}}] }}
    """
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type='application/json')
        )
        return json.loads(response.text)
    except:
        return {"summary": "실패", "places": []}

def summarize_reviews(reviews):
    """리뷰 요약 함수 (에러 수정됨)"""
    if not reviews: return ""
    
    client = get_client()
    
    # [핵심 수정] 리뷰가 딕셔너리인지 문자열인지 확인해서 처리
    cleaned_reviews = []
    for r in reviews[:15]:
        if isinstance(r, dict):
            cleaned_reviews.append(r.get('text', ''))
        elif isinstance(r, str):
            cleaned_reviews.append(r)
        else:
            cleaned_reviews.append(str(r))
            
    review_text = "\n".join(cleaned_reviews)
    
    if not review_text.strip(): return "리뷰 내용 없음"

    try:
        res = client.models.generate_content(
            model=MODEL_NAME, 
            contents=f"이 식당 리뷰들을 3줄로 핵심만 요약해줘: {review_text}"
        )
        return res.text
    except:
        return "요약 실패"
