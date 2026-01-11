import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# 모델 설정 (아까 확인한 2.5 버전 사용)
MODEL_NAME = 'models/gemini-2.5-pro'

def summarize_text(text):
    """
    텍스트를 분석하여 '요약문'과 '검색 키워드 리스트'를 JSON으로 반환
    """
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        
        # 프롬프트: JSON 포맷을 강제함
        prompt = f"""
        너는 여행 정보를 정리하는 AI야. 아래 텍스트를 분석해서 반드시 **JSON 형식**으로만 답변해줘.
        다른 미사여구는 절대 넣지 마.

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
        
        response = model.generate_content(prompt)
        
        # 응답 텍스트에서 JSON 부분만 발라내기 (가끔 ```json ... ``` 이렇게 줄 때가 있음)
        cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
        
        # 파이썬 딕셔너리로 변환
        result_json = json.loads(cleaned_text)
        return result_json
        
    except Exception as e:
        # 에러 발생 시 비상용 깡통 데이터 리턴
        print(f"AI 에러: {e}")
        return {
            "summary": "AI 분석 중 오류가 발생했습니다.",
            "places": []
        }