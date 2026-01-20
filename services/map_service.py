import os
import requests
from dotenv import load_dotenv

load_dotenv()

def get_google_maps_api_key():
    try:
        return os.environ["GOOGLE_MAPS_API_KEY"]
    except KeyError:
        print("Error: GOOGLE_MAPS_API_KEY not found in .env")
        return None

def search_place(query):
    """
    구글 장소 검색 API를 사용하여 장소 정보를 찾습니다.
    """
    api_key = get_google_maps_api_key()
    if not api_key: return None

    # 1. 텍스트 검색 (Find Place Request)
    search_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "input": query,
        "inputtype": "textquery",
        # 필요한 필드만 요청 (비용 절약)
        "fields": "place_id,name,rating,photos,formatted_address",
        "key": api_key
    }
    
    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "OK" and data.get("candidates"):
            candidate = data["candidates"][0]
            result = {
                "place_id": candidate.get("place_id"),
                "name": candidate.get("name"),
                "rating": candidate.get("rating", 0.0),
                "address": candidate.get("formatted_address"),
                "photo_url": None
            }

            # 사진이 있으면 첫 번째 사진의 URL 가져오기
            if candidate.get("photos"):
                photo_reference = candidate["photos"][0]["photo_reference"]
                # 사진 크기는 가로 800px로 요청
                photo_request_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_reference}&key={api_key}"
                # 실제 이미지 URL은 리다이렉트된 최종 주소임
                photo_response = requests.get(photo_request_url, allow_redirects=False)
                if photo_response.status_code == 302:
                    result["photo_url"] = photo_response.headers["Location"]
            
            return result
            
    except Exception as e:
        print(f"Google Maps API Error: {e}")
    
    return None

def get_place_reviews(place_id):
    """
    Place ID로 상세 정보(리뷰 포함)를 가져옵니다.
    """
    api_key = get_google_maps_api_key()
    if not api_key or not place_id: return []
    
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "reviews", # 리뷰만 요청
        "language": "ko",    # 한국어 리뷰 우선
        "key": api_key
    }
    
    try:
        response = requests.get(details_url, params=params)
        data = response.json()
        if data.get("status") == "OK" and data.get("result"):
            return data["result"].get("reviews", [])
    except Exception as e:
        print(f"Review API Error: {e}")
        
    return []

# ================================================================================
# [핵심 수정] QR코드용 링크 생성 함수
# ================================================================================
def get_map_link(place_id):
    """
    Place ID를 기반으로 가장 확실한 구글맵 링크를 생성합니다.
    이 방식(query_place_id)이 모바일/PC 모두에서 가장 잘 작동합니다.
    """
    if not place_id:
        return "https://www.google.com/maps" # 기본 구글맵 주소
        
    # 공식적으로 권장되는 특정 장소 공유 링크 형식
    return f"https://www.google.com/maps/search/?api=1&query=Google&query_place_id={place_id}"
