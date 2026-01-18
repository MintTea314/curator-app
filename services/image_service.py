import qrcode
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os

# 폰트 파일 경로
FONT_PATH = os.path.join("fonts", "Hakgyoansim_OcarinaR.ttf")

def load_font(size):
    """폰트를 불러오는 헬퍼 함수"""
    try:
        # 호환성을 위해 layout_engine 옵션 사용 안 함
        return ImageFont.truetype(FONT_PATH, size)
    except IOError:
        print(f"\n⚠️ [경고] 폰트 파일을 찾을 수 없습니다: {FONT_PATH}")
        return ImageFont.load_default()

def generate_qr_code(link):
    """QR코드 이미지 생성 (크기 180x180)"""
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img.resize((180, 180))

def wrap_text_pixel_based(text, font, max_width):
    """
    주어진 픽셀 너비를 넘어가지 않도록 줄바꿈 (안전한 방식)
    """
    if not text:
        return ""
        
    lines = []
    current_line = ""
    
    for char in text:
        test_line = current_line + char
        # 안전한 너비 계산
        try:
            width = font.getlength(test_line)
        except AttributeError:
            width = font.getsize(test_line)[0] # 구버전 호환

        if width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = char
            
    lines.append(current_line)
    return "\n".join(lines)

def create_restaurant_card(restaurant_data):
    # 1. 캔버스 준비 (600x800)
    canvas_width = 600
    canvas_height = 800
    background_color = (255, 255, 255)
    card = Image.new('RGB', (canvas_width, canvas_height), background_color)
    draw = ImageDraw.Draw(card)

    # 폰트 로드
    font_title = load_font(38)
    font_text = load_font(22)
    # 주소용 작은 폰트는 이제 필요 없음

    # 레이아웃 설정
    margin = 30
    text_start_y = 430 # 텍스트 시작 높이
    qr_size = 180
    # 텍스트가 QR코드를 침범하지 않도록 안전 너비 계산
    safe_text_width = canvas_width - margin - qr_size - 20 

    # --- 상단 이미지 영역 ---
    photo_url = restaurant_data.get('사진URL')
    if photo_url:
        try:
            response = requests.get(photo_url, timeout=5)
            photo = Image.open(io.BytesIO(response.content)).convert("RGB")
            target_height = 400
            aspect_ratio = photo.width / photo.height
            new_width = int(target_height * aspect_ratio)
            photo = photo.resize((new_width, target_height))
            left = (canvas_width - new_width) // 2
            card.paste(photo, (left, 0))
        except Exception as e:
            draw.rectangle([(0,0), (canvas_width, 400)], fill=(200, 200, 200))
            draw.text((200, 180), "사진 없음", font=font_text, fill=(100,100,100))
    else:
        draw.rectangle([(0,0), (canvas_width, 400)], fill=(230, 230, 230))
        draw.text((250, 180), "사진 없음", font=font_text, fill=(100,100,100))

    # --- 하단 정보 영역 ---
    name = restaurant_data.get('식당이름', '이름 모름')
    rating = restaurant_data.get('평점', 0)
    description = restaurant_data.get('특징', '')
    map_link = restaurant_data.get('지도링크')
    # 주소 데이터는 이제 안 씁니다.

    # 폰트 색상
    fill_black = (0, 0, 0)
    fill_orange = (255, 165, 0)
    fill_gray = (50, 50, 50)
    if font_title.getname()[0] == "Default": 
        fill_black = fill_orange = fill_gray = None

    # [수정 1] QR코드 배치 (우측 상단, 타이틀 높이에 맞춤)
    if map_link:
        qr_img = generate_qr_code(map_link)
        qr_x = canvas_width - qr_img.width - margin
        qr_y = text_start_y # 텍스트 시작점과 높이를 맞춥니다.
        card.paste(qr_img, (qr_x, qr_y))

    # --- 텍스트 그리기 (QR코드 왼쪽 영역에) ---
    
    # 1. 식당 이름
    draw.text((margin, text_start_y), name, font=font_title, fill=fill_black)
    
    # 2. 평점
    current_y = text_start_y + 50
    if rating > 0:
        # [수정 2] 하이픈(-) 추가
        draw.text((margin, current_y), f"- ⭐ 구글 평점: {rating}점", font=font_text, fill=fill_orange)
    
    # 3. 특징
    current_y += 50
    if description:
        # [수정 3] 하이픈(-) 추가
        draw.text((margin, current_y), "- 💡 특징:", font=font_text, fill=fill_gray)
        current_y += 30
        # 계산된 안전 너비 내에서 줄바꿈
        wrapped_desc = wrap_text_pixel_based(description, font_text, safe_text_width)
        draw.text((margin, current_y), wrapped_desc, font=font_text, fill=fill_gray)

    # [수정 4] 주소 그리는 부분 완전히 삭제됨

    return card
