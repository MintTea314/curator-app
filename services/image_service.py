import qrcode
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os

FONT_PATH = os.path.join("fonts", "Hakgyoansim_OcarinaR.ttf")

def load_font(size):
    """폰트를 불러오는 헬퍼 함수"""
    try:
        # [수정] 에러를 유발하는 layout_engine 옵션 완전 삭제!
        return ImageFont.truetype(FONT_PATH, size)
    except IOError:
        print(f"\n⚠️ [경고] 폰트 파일을 찾을 수 없습니다: {FONT_PATH}")
        return ImageFont.load_default()

def generate_qr_code(link):
    """QR코드 생성 (120px)"""
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img.resize((120, 120))

def wrap_text_pixel_based(text, font, max_width):
    """안전한 줄바꿈 함수"""
    if not text: return ""
    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        try: width = font.getlength(test_line)
        except AttributeError: width = font.getsize(test_line)[0]
        
        if width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = char
    lines.append(current_line)
    return "\n".join(lines)

def draw_list_item(draw, x, y, icon, text, font, color, max_width):
    """항목 그리기 (하이픈 간격 좁게)"""
    # 1. 하이픈
    draw.text((x, y), "-", font=font, fill=color)
    try: hyphen_width = font.getlength("-")
    except AttributeError: hyphen_width = font.getsize("-")[0]
    
    # 간격 좁히기 (-4px)
    text_x = x + hyphen_width - 4
    
    # 2. 본문
    full_text = f"{icon} {text}" if icon else text
    wrapped_text = wrap_text_pixel_based(full_text, font, max_width - (text_x - x))
    draw.text((text_x, y), wrapped_text, font=font, fill=color)
    
    # 다음 줄 높이 계산 (줄바꿈 수 * 30px + 여백 10px)
    lines_count = wrapped_text.count('\n') + 1
    return y + (lines_count * 30) + 10 

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
    
    # 가로폭 넓게 사용 (QR코드가 하단으로 갔으므로)
    full_text_width = canvas_width - (margin * 2)

    # --- 상단 이미지 ---
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
        except:
            draw.rectangle([(0,0), (canvas_width, 400)], fill=(200, 200, 200))
            draw.text((200, 180), "사진 없음", font=font_text, fill=(100,100,100))
    else:
        draw.rectangle([(0,0), (canvas_width, 400)], fill=(230, 230, 230))
        draw.text((250, 180), "사진 없음", font=font_text, fill=(100,100,100))

    # --- 정보 가져오기 ---
    name = restaurant_data.get('식당이름', '이름 모름')
    rating = restaurant_data.get('평점', 0)
    description = restaurant_data.get('특징', '')
    review_summ = restaurant_data.get('리뷰요약', '') # 리뷰 요약 추가
    map_link = restaurant_data.get('지도링크')

    # 색상 설정
    fill_black = (0, 0, 0)
    fill_orange = (255, 165, 0)
    fill_gray = (50, 50, 50)
    fill_blue = (30, 100, 200) # 파란색 (리뷰용)
    
    if font_title.getname()[0] == "Default": 
        fill_black = fill_orange = fill_gray = fill_blue = None

    # --- 하단 QR코드 (우측 구석) ---
    if map_link:
        qr_img = generate_qr_code(map_link)
        qr_x = canvas_width - qr_img.width - margin
        qr_y = canvas_height - qr_img.height - margin
        card.paste(qr_img, (qr_x, qr_y))

    # --- 텍스트 그리기 (차곡차곡 쌓기) ---
    
    # 1. 식당 이름
    draw.text((margin, text_start_y), name, font=font_title, fill=fill_black)
    current_y = text_start_y + 50
    
    # 2. 평점
    if rating > 0:
        current_y = draw_list_item(
            draw, margin, current_y, "⭐", 
            f"구글 평점: {rating}점", 
            font_text, fill_orange, full_text_width
        )
    
    # 3. 특징 (영상 내용)
    if description:
        current_y = draw_list_item(
            draw, margin, current_y, "💡", 
            f"특징: {description}", 
            font_text, fill_gray, full_text_width
        )

    # 4. 후기 요약 (구글 리뷰) - 파란색
    if review_summ:
        draw_list_item(
            draw, margin, current_y, "🗣️", 
            f"후기: {review_summ}", 
            font_text, fill_blue, full_text_width
        )

    return card
