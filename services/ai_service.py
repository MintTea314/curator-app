import os
import json
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def summarize_text(text):
    # 1. API 키 가져오기 (클라우드 우선, 없으면 로컬)
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except:
        api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        return {"summary": "API 키 오류: Streamlit Secrets 설정을 확인해주세요.", "places": []}

    try:
        # 2. 클라이언트 연결
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
        너는 여행 정보를 정리하는 AI야. 아래 텍스트를 분석해서 반드시 **JSON 형식**으로만 답변해줘.
        
        [분석할 텍스트]
        {text}

        [필수 답변 형식 (JSON)]
        {{
            "summary": "전체 내용을 3줄로 요약한 텍스트 (한국어)",
            "places": [
                {{
                    "search_query": "구글 지도에 검색할 정확한 가게 이름 (예: 후쿠오카 카와미야 함바그)",
                    "description": "이 가게의 핵심 특징 한 줄 요약"
                }}
            ]
        }}
        """

        # [수정] 모델을 최신 2.0 버전으로 변경 (에러 해결의 핵심)
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
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
        # 에러 메시지를 좀 더 자세히 출력해서 디버깅을 돕습니다.
        print(f"AI 에러 상세: {e}")
        return {
            "summary": f"AI 분석 실패. (모델: gemini-2.0-flash-exp)\n에러 메시지: {str(e)}",
            "places": []
        }
