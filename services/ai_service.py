import os
import json
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

def summarize_text(text):
    # (기존 함수 내용 유지)
    client = get_client()
    
    prompt = f"""
    너는 '여행 맛집 데이터 복원 전문가'야.
    아래 텍스트는 유튜브 자동 자막이라서 **고유명사(식당 이름)가 발음대로 잘못 적혀있거나 오타가 심해.**
    
    네가 가진 방대한 여행 지식을 동원해서 **문맥을 보고 원래 식당 이름을 추리해서 복원해.**
    
    [오타 복원 예시]
    - "냉무옹호" -> "넹무옵 (Neng Earthen Jar Roast Pork)"
    - "창포와 모크라" -> "창푸악 무끄라타 (Chang Phueak Mukrata)"
    - "블루들한 갈비국수" -> "블루누들 (Blue Noodle)"
    
    [분석할 자막 텍스트]
    {text}

    [필수 답변 형식 (JSON)]
    반드시 아래 JSON 형식으로만 답해줘. 식당 이름은 구글 지도에서 검색 잘 되는 정확한 명칭(한국어+영어 병기)으로 고쳐줘.
    {{
        "summary": "전체 내용을 3줄로 요약한 텍스트 (한국어)",
        "places": [
            {{
                "search_query": "복원된 정확한 식당 이름 (예: 치앙마이 넹무옵)",
                "description": "이 가게의 핵심 특징 및 가격 정보 한 줄 요약"
            }}
        ]
    }}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type='application/json')
        )
        if response.text: return json.loads(response.text)
        return {"summary": "AI 응답 비어있음", "places": []}
    except Exception as e:
        return {"summary": f"에러: {str(e)}", "places": []}

def summarize_reviews(reviews_list):
    """
    [신규 기능] 구글 리뷰 리스트를 받아 2줄로 요약합니다.
    """
    if not reviews_list:
        return ""
    
    client = get_client()
    reviews_text = "\n".join(reviews_list)
    
    prompt = f"""
    아래는 식당의 구글 맵 실제 리뷰들이다.
    사람들의 공통된 의견(맛, 분위기, 친절도 등)을 종합해서 **딱 2줄로 요약해줘.**
    말투는 "~함", "~임" 처럼 간결한 명사형으로 끝내줘.
    
    [리뷰 목록]
    {reviews_text}
    
    [답변 형식]
    (예시)
    국물이 진하고 고기가 부드러워 해장하기 좋음.
    웨이팅이 길지만 회전율이 빠르고 직원이 친절함.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )
        return response.text.strip()
    except Exception:
        return ""
