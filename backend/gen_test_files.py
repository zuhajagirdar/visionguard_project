from PIL import Image, ImageDraw
def create_valid_image(path):
    img = Image.new('RGB', (400, 200), color = (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((10,10), "Test Merchant\\nDate: 2026-10-01\\nTotal: 150.00", fill=(0,0,0))
    img.save(path)
def create_valid_pdf(path):
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(path)
    c.drawString(100, 750, "Test")
    c.drawString(100, 735, "Date: 2026-10-01")
    c.drawString(100, 720, "Total: 150.00")
    c.save()
