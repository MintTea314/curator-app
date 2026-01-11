import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# [중요] 최신 라이브러리(google-genai) 사용 방식
def summarize_text(text):
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        return {"summary": "API 키가 없습니다.", "places": []}

    try:
        # 1. 클라이언트 연결 (신형 방식)
        client = genai.Client(api_key=api_key)
        
        # 2. 프롬프트 작성
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

        # 3. AI에게 요청 (모델은 1.5-flash가 가성비/속도 최고입니다)
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json' # JSON 강제 출력 기능
            )
        )
        
        # 4. 결과 처리
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
