from PIL import Image, ImageDraw, ImageFont

def create_valid_image(path, merchant="Test Merchant", date="2026-10-01", total="150.00"):
    img = Image.new('RGB', (800, 400), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 32)
    except Exception:
        font = ImageFont.load_default()
    text_lines = f"{merchant}\nDate: {date}\nTotal: {total}\n"
    d.text((50, 50), text_lines, fill=(0, 0, 0), font=font)
    img.save(path)

def create_valid_pdf(path, merchant="Test", date="2026-10-01", total="150.00"):
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(path)
    c.drawString(100, 750, str(merchant))
    c.drawString(100, 735, f"Date: {date}")
    c.drawString(100, 720, f"Total: {total}")
    c.save()
