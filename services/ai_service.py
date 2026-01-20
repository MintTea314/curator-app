import os
import json
import time
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# 선생님의 2.5 Pro 모델 유지
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
        with open(video_path, "rb") as f:
            upload_result = client.files.upload(
                file=f, 
                config=types.UploadFileConfig(mime_type='video/mp4')
            )
        
        while True:
            file_meta = client.files.get(name=upload_result.name)
            if file_meta.state == "ACTIVE":
                break
            elif file_meta.state == "FAILED":
                return {"summary": "영상 처리 실패", "places": []}
            time.sleep(1)

        # [프롬프트 수정] "display_name"을 추가해서 카드용(한글/영어) 이름을 따로 받음
        prompt = """
        이 영상을 분석해서 맛집 정보를 JSON으로 줘.
        
        [미션]
        1. **시각(OCR):** 간판, 메뉴판을 읽어 상호명을 찾아.
        2. **청각:** 맛 표현이나 특징을 들어.
        
        [출력 형식]
        {{
            "summary": "영상 내용 3줄 요약",
            "places": [
                {{
                    "search_query": "구글 검색용 정확한 이름 (현지어 포함 가능)",
                    "display_name": "카드에 적을 깔끔한 이름 (특수문자 제외, 한국어 또는 영어로만)", 
                    "description": "특징 설명"
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
        return {"summary": f"에러: {str(e)}", "places": []}

def analyze_text(text):
    client = get_client()
    # 텍스트 분석에서도 display_name 요청
    prompt = f"""
    맛집 정보 추출. JSON 포맷.
    텍스트: {text[:20000]} 
    Format: {{ "summary": "요약", "places": [{{"search_query": "검색용이름", "display_name": "한국어/영어이름", "description": "특징"}}] }}
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
    """리뷰 요약 함수 (말대꾸 금지 기능 추가)"""
    if not reviews: return ""
    
    client = get_client()
    cleaned_reviews = []
    for r in reviews[:15]:
        if isinstance(r, dict): cleaned_reviews.append(r.get('text', ''))
        elif isinstance(r, str): cleaned_reviews.append(r)
        else: cleaned_reviews.append(str(r))
            
    review_text = "\n".join(cleaned_reviews)
    if not review_text.strip(): return "리뷰 없음"

    try:
        # [프롬프트 수정] "바로 요약 내용만 말해"라고 지시
        prompt = f"""
        이 식당 리뷰들을 읽고 한국어로 3줄 이내로 핵심만 요약해.
        
        [절대 금지]
        - "네, 알겠습니다" 같은 인사말 하지 마.
        - "요약해 드릴게요" 같은 말 하지 마.
        - 바로 요약된 문장부터 시작해.
        
        리뷰들: {review_text}
        """
        res = client.models.generate_content(
            model=MODEL_NAME, 
            contents=prompt
        )
        return res.text
    except:
        return "요약 실패"
