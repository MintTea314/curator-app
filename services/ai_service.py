import os
import json
import streamlit as st # [추가] 스트림릿 기능 가져오기
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def summarize_text(text):
    # [수정] 클라우드(secrets) 먼저 확인하고, 없으면 내 컴퓨터(env) 확인
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except:
        api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        return {"summary": "API 키가 없습니다. Streamlit Secrets 설정을 확인해주세요.", "places": []}

    try:
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

        response = client.models.generate_content(
            model='gemini-1.5-flash',
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
        print(f"AI 에러: {e}")
        return {
            "summary": f"분석 중 오류가 발생했습니다: {str(e)}",
            "places": []
        }
