import os
import json
import time
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# 선생님이 지정하신 모델명 (만약 이 모델이 없으면 에러 메시지로 알려줍니다)
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

    # 1. 파일 존재 확인
    if not os.path.exists(video_path):
        return {"summary": "영상 파일 없음", "places": []}
        
    file_size = os.path.getsize(video_path)
    print(f"📁 영상 파일 확인됨: {video_path} (크기: {file_size/1024/1024:.2f} MB)")

    try:
        print("🚀 [1단계] 구글 서버로 영상 업로드 시작...")
        
        # [핵심 수정] 
        # 1. 'path=' 대신 'file=' 사용 (에러 해결)
        # 2. f.read() 대신 f 자체를 전달 (메모리 폭발 방지 & 자동 스트리밍)
        with open(video_path, "rb") as f:
            upload_result = client.files.upload(
                file=f, 
                config=types.UploadFileConfig(mime_type='video/mp4')
            )
        
        print(f"✅ [1단계 완료] 업로드 성공! (이름: {upload_result.name})")
        
        # 3. 처리 대기
        print("⏳ [2단계] 구글측 영상 처리 대기 중...")
        while True:
            file_meta = client.files.get(name=upload_result.name)
            if file_meta.state == "ACTIVE":
                print("✅ [2단계 완료] 영상 처리 완료! (ACTIVE)")
                break
            elif file_meta.state == "FAILED":
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
        print(f"💥 [에러 발생] {str(e)}")
        # 모델명 문제일 경우 힌트 제공
        if "404" in str(e) or "Not Found" in str(e):
             return {"summary": f"🚨 모델 오류: '{MODEL_NAME}' 모델을 찾을 수 없습니다. (gemini-1.5-pro 또는 gemini-2.0-flash로 변경해보세요)", "places": []}
        return {"summary": f"시스템 에러: {str(e)}", "places": []}

# --- (기존 텍스트 분석 함수들은 그대로 유지) ---
def analyze_text(text):
    client = get_client()
    prompt = f"""
    다음 텍스트에서 맛집 정보를 추출해줘. JSON 형식으로.
    텍스트: {text[:20000]} 
    Format:
    {{ "summary": "요약", "places": [{{"search_query": "식당이름", "description": "특징"}}] }}
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
    if not reviews: return ""
    client = get_client()
    review_text = "\n".join([r['text'] for r in reviews[:15]])
    try:
        res = client.models.generate_content(model=MODEL_NAME, contents=f"3줄 요약: {review_text}")
        return res.text
    except:
        return "요약 실패"
