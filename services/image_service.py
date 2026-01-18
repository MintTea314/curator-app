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
        # [수정] 호환성을 위해 layout_engine 옵션 제거 (이게 에러 원인이었습니다)
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
    주어진 픽셀 너비를 넘어가지 않도록 줄바꿈
    """
    if not text:
        return ""
        
    lines = []
    current_line = ""
    
    for char in text:
        test_line = current_line + char
        # getlength는 구버전 Pillow에서도 대부분 지원하지만, 혹시 모를 안전장치
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
    # 1. 캔버스 준비
    canvas_width = 600
    canvas_height = 800
    background_color = (255, 255, 255)
    card = Image.new('RGB', (canvas_width, canvas_height), background_color)
    draw = ImageDraw.Draw(card)

    # 폰트 로드
    font_title = load_font(38)
    font_text = load_font(22)
    font_small = load_font(16)

    margin = 30
    text_start_y = 430
    qr_size = 180
    safe_text_width = canvas_width - margin - qr_size - 20 

    # --- 이미지 다운로드 ---
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

    # --- 텍스트 그리기 ---
    name = restaurant_data.get('식당이름', '이름 모름')
    rating = restaurant_data.get('평점', 0)
    description = restaurant_data.get('특징', '')
    address = restaurant_data.get('주소', '')
    map_link = restaurant_data.get('지도링크')

    fill_black = (0, 0, 0)
    fill_orange = (255, 165, 0)
    fill_gray = (50, 50, 50)
    fill_light_gray = (100, 100, 100)
    
    if font_title.getname()[0] == "Default": 
        fill_black = fill_orange = fill_gray = fill_light_gray = None

    draw.text((margin, text_start_y), name, font=font_title, fill=fill_black)
    
    current_y = text_start_y + 50
    if rating > 0:
        draw.text((margin, current_y), f"⭐ 구글 평점: {rating}점", font=font_text, fill=fill_orange)
    
    current_y += 50
    if description:
        draw.text((margin, current_y), "💡 특징:", font=font_text, fill=fill_gray)
        current_y += 30
        wrapped_desc = wrap_text_pixel_based(description, font_text, safe_text_width)
        draw.text((margin, current_y), wrapped_desc, font=font_text, fill=fill_gray)

    if map_link:
        qr_img = generate_qr_code(map_link)
        qr_x = canvas_width - qr_img.width - margin
        qr_y = canvas_height - qr_img.height - margin
        card.paste(qr_img, (qr_x, qr_y))

    if address:
        address_y = canvas_height - margin - 20
        final_address = address
        
        # 주소 길이 계산 (안전하게 처리)
        try:
            addr_width = font_small.getlength("📍 " + address)
        except:
            addr_width = font_small.getsize("📍 " + address)[0]

        if addr_width > safe_text_width:
            for i in range(len(address), 0, -1):
                temp_addr = "📍 " + address[:i] + "..."
                try:
                    w = font_small.getlength(temp_addr)
                except:
                    w = font_small.getsize(temp_addr)[0]
                
                if w <= safe_text_width:
                    final_address = address[:i] + "..."
                    break
        else:
            final_address = "📍 " + address

        draw.text((margin, address_y), final_address, font=font_small, fill=fill_light_gray)

    return card
