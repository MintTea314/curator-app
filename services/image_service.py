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
        return ImageFont.truetype(FONT_PATH, size)
    except IOError:
        print(f"\n⚠️ [경고] 폰트 파일을 찾을 수 없습니다: {FONT_PATH}")
        return ImageFont.load_default()

def generate_qr_code(link):
    """QR코드 이미지 생성"""
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    # [수정 1] 사이즈를 100px로 축소 (기존 135px의 약 3/4)
    return img.resize((100, 100))

def wrap_text_pixel_based(text, font, max_width):
    """안전한 줄바꿈 함수"""
    if not text: return ""
    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        try: width = font.getlength(test_line)
        except AttributeError: width = font.getsize(test_line)[0]
        if width <= max_width: current_line = test_line
        else: lines.append(current_line); current_line = char
    lines.append(current_line)
    return "\n".join(lines)

def draw_list_item(draw, x, y, icon, text, font, color, max_width):
    """
    [신규 기능] 하이픈과 텍스트 사이 간격을 정밀 조절하는 함수
    """
    # 1. 하이픈 그리기
    draw.text((x, y), "-", font=font, fill=color)
    
    # 2. 텍스트 위치 계산 (하이픈 너비 - 4px 만큼 당겨서 출력)
    try:
        hyphen_width = font.getlength("-")
    except AttributeError:
        hyphen_width = font.getsize("-")[0]
        
    # [수정 2] 간격을 줄이기 위해 오프셋을 살짝 뺍니다 (-4px)
    text_x = x + hyphen_width - 4
    
    # 3. 아이콘+텍스트 그리기
    full_text = f"{icon} {text}" if icon else text
    
    # 줄바꿈 처리
    wrapped_text = wrap_text_pixel_based(full_text, font, max_width - (text_x - x))
    draw.text((text_x, y), wrapped_text, font=font, fill=color)

def create_restaurant_card(restaurant_data):
    # 1. 캔버스 준비 (600x800)
    canvas_width = 600
    canvas_height = 800
    background_color = (255, 255, 255)
    card = Image.new('RGB', (canvas_width, canvas_height), background_color)
    draw = ImageDraw.Draw(card)

    font_title = load_font(38)
    font_text = load_font(22)

    margin = 30
    text_start_y = 430
    
    # [수정 1 관련] QR코드 사이즈와 여백 재설정
    qr_size = 100
    qr_right_margin = 0 # 오른쪽 끝에 딱 붙임

    safe_text_width = canvas_width - margin - qr_size - qr_right_margin - 20

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
        except Exception:
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

    fill_black = (0, 0, 0)
    fill_orange = (255, 165, 0)
    fill_gray = (50, 50, 50)
    if font_title.getname()[0] == "Default": 
        fill_black = fill_orange = fill_gray = None

    # [수정 3] QR코드 배치 (완전 오른쪽 끝)
    if map_link:
        qr_img = generate_qr_code(map_link)
        qr_x = canvas_width - qr_img.width - qr_right_margin
        qr_y = text_start_y
        card.paste(qr_img, (qr_x, qr_y))

    # --- 텍스트 그리기 ---
    # 1. 식당 이름
    draw.text((margin, text_start_y), name, font=font_title, fill=fill_black)
    
    # 2. 평점 (리스트 함수 사용)
    current_y = text_start_y + 50
    if rating > 0:
        draw_list_item(
            draw, margin, current_y, "⭐", 
            f"구글 평점: {rating}점", 
            font_text, fill_orange, safe_text_width
        )
    
    # 3. 특징 (리스트 함수 사용)
    current_y += 50
    if description:
        draw_list_item(
            draw, margin, current_y, "💡", 
            f"특징: {description}", 
            font_text, fill_gray, safe_text_width
        )

    return card
