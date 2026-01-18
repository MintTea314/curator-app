import os
import json
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def summarize_text(text):
    # 1. API 키 가져오기
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except:
        api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        return {"summary": "API 키 오류: Streamlit Secrets 설정을 확인해주세요.", "places": []}

    try:
        client = genai.Client(api_key=api_key)
        
        # [핵심] 오타 복원을 위한 강력한 프롬프트
        prompt = f"""
        너는 '여행 맛집 데이터 복원 전문가'야.
        아래 텍스트는 유튜브 자동 자막이라서 **고유명사(식당 이름)가 발음대로 잘못 적혀있거나 오타가 심해.**
        
        네가 가진 방대한 여행 지식을 동원해서 **문맥을 보고 원래 식당 이름을 추리해서 복원해.**
        
        [오타 복원 예시]
        - "냉무옹호" -> (치앙마이 문맥) -> "넹무옵 (Neng Earthen Jar Roast Pork)"
        - "창포와 모크라" -> (무한리필 문맥) -> "창푸악 무끄라타 (Chang Phueak Mukrata)"
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

        # 추리력이 좋은 Pro 모델 사용
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp', # 혹은 gemini-1.5-pro
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json'
            )
        )
        
        if response.text:
            return json.loads(response.text)
        else:
            return {"summary": "AI 응답이 비어있습니다.", "places": []}
            
    except Exception as e:
        print(f"AI 에러 상세: {e}")
        return {
            "summary": f"AI 분석 실패: {str(e)}",
            "places": []
        }
