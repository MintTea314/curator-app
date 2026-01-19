import qrcode
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os

# [수정 1] Noto Sans 폰트 파일명 확인 (정확한 파일명으로 수정해주세요)
# 예: 'NotoSansKR-Regular.ttf', 'NotoSansKR-Bold.ttf'
FONT_PATH_REG = os.path.join("fonts", "NotoSansKR-Regular.ttf")
FONT_PATH_BOLD = os.path.join("fonts", "NotoSansKR-Bold.ttf")

def load_font(size, is_bold=False):
    font_path = FONT_PATH_BOLD if is_bold else FONT_PATH_REG
    try:
        return ImageFont.truetype(font_path, size)
    except IOError:
        return ImageFont.load_default()

def generate_qr_code(link):
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img.resize((120, 120))

def wrap_text_smart(text, font, max_width):
    """단어 단위 안전 줄바꿈"""
    if not text: return ""
    words = text.split(' ')
    lines = []
    current_line = []
    for word in words:
        test_line = ' '.join(current_line + [word])
        try: width = font.getlength(test_line)
        except AttributeError: width = font.getsize(test_line)[0]
        if width <= max_width: current_line.append(word)
        else:
            if current_line: lines.append(' '.join(current_line))
            current_line = [word]
    if current_line: lines.append(' '.join(current_line))
    return "\n".join(lines)

def draw_list_item(draw, x, y, icon, text, font, color, max_width):
    """
    [수정 2] 하이픈 제거 & 이모티콘 적용
    """
    # 이모티콘+텍스트 결합
    full_text = f"{icon} {text}"
    
    # 스마트 줄바꿈
    wrapped_text = wrap_text_smart(full_text, font, max_width)
    
    # 텍스트 그리기
    draw.text((x, y), wrapped_text, font=font, fill=color)
    
    # 다음 줄 높이 계산 (Noto Sans 줄 간격 고려하여 넉넉하게 34px)
    lines_count = wrapped_text.count('\n') + 1
    return y + (lines_count * 34) + 10 

def create_restaurant_card(restaurant_data):
    canvas_width = 600
    canvas_height = 800
    background_color = (255, 255, 255)
    card = Image.new('RGB', (canvas_width, canvas_height), background_color)
    draw = ImageDraw.Draw(card)

    # [수정 3] 폰트 크기 축소 (제목 36, 본문 20)
    font_title = load_font(36, is_bold=True)
    font_text = load_font(20, is_bold=False)

    margin = 30
    text_start_y = 430
    qr_size = 120
    # [수정 4] QR코드 여백을 10px로 줄임
    qr_margin = 10
    
    map_link = restaurant_data.get('지도링크')

    # [수정 5] 텍스트 안전 너비 재계산 (QR코드 여백 감소 반영)
    if map_link:
        # 전체폭 - 왼쪽마진 - QR폭 - QR오른쪽마진(10) - 간격(20)
        safe_text_width = canvas_width - margin - qr_size - qr_margin - 20
    else:
        safe_text_width = canvas_width - (margin * 2)

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
    review_summ = restaurant_data.get('리뷰요약', '')
    
    # 색상 설정
    fill_black = (0, 0, 0)
    fill_orange = (255, 165, 0)
    fill_gray = (50, 50, 50)
    fill_blue = (30, 100, 200)
    if font_title.getname()[0] == "Default": 
        fill_black = fill_orange = fill_gray = fill_blue = None

    # --- 하단 QR코드 (우측 구석, 여백 10px) ---
    if map_link:
        qr_img = generate_qr_code(map_link)
        qr_x = canvas_width - qr_img.width - qr_margin # 10px 여백
        qr_y = canvas_height - qr_img.height - qr_margin # 10px 여백
        card.paste(qr_img, (qr_x, qr_y))

    # --- 텍스트 그리기 ---
    # 1. 식당 이름
    draw.text((margin, text_start_y), name, font=font_title, fill=fill_black)
    current_y = text_start_y + 50
    
    # 2. 평점 (⭐ 이모지 사용)
    if rating > 0:
        current_y = draw_list_item(
            draw, margin, current_y, "⭐", # [수정] 이모지 변경
            f"구글 평점: {rating}점", 
            font_text, fill_orange, safe_text_width
        )
    
    # 3. 특징 (💡 이모지 사용)
    if description:
        current_y = draw_list_item(
            draw, margin, current_y, "💡", # [수정] 이모지 변경
            f"특징: {description}", 
            font_text, fill_gray, safe_text_width
        )

    # 4. 후기 요약 (🗣️ 이모지 사용)
    if review_summ:
        draw_list_item(
            draw, margin, current_y, "🗣️", # [수정] 이모지 변경
            f"후기: {review_summ}", 
            font_text, fill_blue, safe_text_width
        )

    return card
