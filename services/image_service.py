import qrcode
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os

# 폰트 파일 경로 지정 (fonts 폴더 안에 NanumGothic.ttf가 있어야 함)
FONT_PATH = os.path.join("fonts", "NanumGothic.ttf")

def load_font(size):
    """폰트를 불러오는 헬퍼 함수 (폰트 파일 없으면 기본 폰트 사용)"""
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except IOError:
        print(f"⚠️ 폰트 파일을 찾을 수 없습니다: {FONT_PATH}. 기본 폰트를 사용합니다.")
        return ImageFont.load_default()

def generate_qr_code(link):
    """링크를 받아서 QR코드 이미지 생성"""
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img.resize((150, 150)) # QR코드 크기 조절

def create_restaurant_card(restaurant_data):
    """맛집 데이터를 받아 카드 뉴스 형태의 이미지를 생성합니다."""
    
    # 1. 캔버스 준비 (흰색 배경, 600x800 크기)
    canvas_width = 600
    canvas_height = 800
    background_color = (255, 255, 255)
    card = Image.new('RGB', (canvas_width, canvas_height), background_color)
    draw = ImageDraw.Draw(card)

    # 폰트 준비
    font_title = load_font(40) # 제목용 큰 폰트
    font_text = load_font(24)  # 본문용 중간 폰트
    font_small = load_font(18) # 주소용 작은 폰트

    # 2. 상단 이미지 영역 채우기
    photo_url = restaurant_data.get('사진URL')
    if photo_url:
        try:
            # 구글 서버에서 이미지 다운로드
            response = requests.get(photo_url, timeout=5)
            photo = Image.open(io.BytesIO(response.content)).convert("RGB")
            
            # 이미지 크기 조정 및 중앙 크롭 (캔버스 상단 절반)
            target_height = 400
            aspect_ratio = photo.width / photo.height
            new_width = int(target_height * aspect_ratio)
            photo = photo.resize((new_width, target_height))
            
            # 중앙에 배치
            left = (canvas_width - new_width) // 2
            card.paste(photo, (left, 0))
        except Exception as e:
            print(f"이미지 다운로드 실패: {e}")
            # 실패 시 회색 박스로 대체
            draw.rectangle([(0,0), (canvas_width, 400)], fill=(200, 200, 200))
            draw.text((200, 180), "사진을 불러올 수 없음", font=font_text, fill=(100,100,100))
    else:
        # 사진 데이터가 없는 경우
        draw.rectangle([(0,0), (canvas_width, 400)], fill=(230, 230, 230))
        draw.text((250, 180), "사진 없음", font=font_text, fill=(100,100,100))

    # 3. 하단 정보 영역 그리기
    text_start_y = 430
    margin = 30
    
    # 3-1. 식당 이름 & 평점
    name = restaurant_data.get('식당이름', '이름 모름')
    rating = restaurant_data.get('평점', 0)
    
    draw.text((margin, text_start_y), name, font=font_title, fill=(0, 0, 0))
    if rating > 0:
        draw.text((margin, text_start_y + 50), f"⭐ 구글 평점: {rating}점", font=font_text, fill=(255, 165, 0)) # 주황색

    # 3-2. 특징 (AI 요약)
    description = restaurant_data.get('특징', '')
    if description:
        # 텍스트 줄바꿈 처리 (너무 길면 잘리니까)
        import textwrap
        wrapped_desc = textwrap.fill(description, width=25) # 약 25글자마다 줄바꿈
        draw.text((margin, text_start_y + 100), f"💡 특징:\n{wrapped_desc}", font=font_text, fill=(50, 50, 50))

    # 4. QR코드 생성 및 배치 (우측 하단)
    map_link = restaurant_data.get('지도링크')
    if map_link:
        qr_img = generate_qr_code(map_link)
        qr_x = canvas_width - qr_img.width - margin
        qr_y = canvas_height - qr_img.height - margin
        card.paste(qr_img, (qr_x, qr_y))
        
        # QR코드 안내 문구
        draw.text((qr_x - 60, qr_y + 110), "Scan for Map ➡️", font=font_small, fill=(100,100,100))

    # 5. 주소 (좌측 하단)
    address = restaurant_data.get('주소', '')
    if address:
        # 주소가 너무 길면 앞부분만 표시
        short_address = address[:30] + "..." if len(address) > 30 else address
        draw.text((margin, canvas_height - 50), f"📍 {short_address}", font=font_small, fill=(100, 100, 100))

    return card
