import os
import requests
from dotenv import load_dotenv

load_dotenv()

def search_place(query):
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        print("❌ [오류] .env 파일에 구글 맵 API 키가 없습니다.")
        return None

    url = "https://places.googleapis.com/v1/places:searchText"

    # [수정] places.photos 필드 추가
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.photos"
    }

    payload = {
        "textQuery": query,
        "languageCode": "ko"
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()

        if "error" in data:
            print(f"\n⚠️ 구글 맵 검색 실패! (검색어: {query})")
            return None

        if data.get("places"):
            place = data["places"][0]
            
            # [추가] 사진 URL 생성 로직
            photo_url = None
            if place.get("photos"):
                # 첫 번째 사진의 리소스 이름 가져오기
                photo_resource = place["photos"][0]["name"]
                # 이미지 불러오는 API URL 완성 (최대 크기 400px 제한)
                photo_url = f"https://places.googleapis.com/v1/{photo_resource}/media?maxHeightPx=400&maxWidthPx=400&key={api_key}"

            return {
                "name": place.get("displayName", {}).get("text", query),
                "address": place.get("formattedAddress", "주소 정보 없음"),
                "rating": place.get("rating", "정보 없음"),
                "user_ratings_total": place.get("userRatingCount", 0),
                "place_id": place.get("id"),
                "photo_url": photo_url # 사진 주소 추가됨
            }
        else:
            return None

    except Exception as e:
        print(f"❌ 시스템 에러: {e}")
        return None

def get_map_link(place_id):
    if not place_id: return "https://www.google.com/maps"
    return f"https://www.google.com/maps/search/?api=1&query=Google&query_place_id={place_id}"