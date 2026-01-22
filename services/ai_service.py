import os
import json
import time
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = 'gemini-2.5-pro'

def get_client():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except:
        api_key = os.getenv("GEMINI_API_KEY")
    return genai.Client(api_key=api_key)

# [1] 영상 분석 (유튜브/릴스)
def analyze_video(video_path):
    client = get_client()

    if not os.path.exists(video_path):
        return {"summary": "파일 없음", "places": []}
        
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

        prompt = """
        이 영상을 분석해서 맛집 정보를 JSON으로 줘.
        
        [미션]
        1. **시각(OCR):** 간판, 메뉴판을 읽어 상호명을 찾아.
        2. **청각:** 맛 표현이나 특징을 들어.
        3. **이름:** display_name 필드에는 특수문자 없이 한국어/영어로 깔끔하게 적어줘.
        
        [출력 형식]
        {{
            "summary": "영상 내용 3줄 요약",
            "places": [
                {{
                    "search_query": "구글 검색용 정확한 이름 (현지어 포함)",
                    "display_name": "카드용 깔끔한 이름 (한글/영어)",
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

# [2] 이미지 분석 (인스타 사진 게시물) - 신규 추가!
def analyze_images(image_paths):
    client = get_client()
    
    if not image_paths:
        return {"summary": "이미지 없음", "places": []}

    try:
        print(f"🖼️ 이미지 {len(image_paths)}장 분석 시작...")
        
        # 이미지 파일들을 업로드
        uploaded_files = []
        for path in image_paths:
            with open(path, "rb") as f:
                # 이미지 업로드 (작은 파일이라 금방 됨)
                up_file = client.files.upload(file=f, config=types.UploadFileConfig(mime_type='image/jpeg'))
                uploaded_files.append(up_file)
        
        prompt = """
        이 사진들은 인스타그램 맛집 게시물이야. 사진 속 음식과 메뉴판, 간판 등을 분석해줘.
        
        [미션]
        1. **시각 정보:** 메뉴판 텍스트나 간판을 읽어서 식당 이름을 찾아내.
        2. **음식 분석:** 사진에 나온 음식이 뭔지 파악해서 설명해.
        
        [출력 형식]
        {{
            "summary": "사진 속 맛집 분위기와 음식 요약 (3줄)",
            "places": [
                {{
                    "search_query": "식당 이름 + 지역 (추정)",
                    "display_name": "카드용 깔끔한 이름 (한글/영어)",
                    "description": "사진에서 보이는 음식 특징과 분위기"
                }}
            ]
        }}
        """
        
        # 프롬프트 + 이미지들 전송
        contents = [prompt] + uploaded_files
        
        response = client.models.generate_content(
            model=MODEL_NAME, 
            contents=contents,
            config=types.GenerateContentConfig(response_mime_type='application/json')
        )
        return json.loads(response.text)

    except Exception as e:
        return {"summary": f"이미지 분석 에러: {str(e)}", "places": []}

# [3] 텍스트 분석
def analyze_text(text):
    client = get_client()
    prompt = f"""
    맛집 정보 추출. JSON 포맷.
    텍스트: {text[:20000]} 
    Format: {{ "summary": "요약", "places": [{{"search_query": "이름", "display_name": "이름(한/영)", "description": "특징"}}] }}
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

# [4] 리뷰 요약
def summarize_reviews(reviews):
    if not reviews: return ""
    client = get_client()
    cleaned = []
    for r in reviews[:15]:
        txt = r.get('text', '') if isinstance(r, dict) else str(r)
        if txt: cleaned.append(txt)
    review_text = "\n".join(cleaned)
    if not review_text.strip(): return "리뷰 없음"

    try:
        res = client.models.generate_content(
            model=MODEL_NAME, 
            contents=f"리뷰 3줄 요약 (인사말 생략, 바로 본론): {review_text}"
        )
        return res.text
    except:
        return "요약 실패"
