import base64
from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List
from PIL import Image, ImageEnhance
from io import BytesIO

app = FastAPI()
templates = Jinja2Templates(directory="templates")

WATERMARK_PATH = "static/hv.png"

def add_watermark_to_image(image_file, watermark_path):
    base = Image.open(image_file).convert("RGBA")
    watermark = Image.open(watermark_path).convert("RGBA")

    scale_factor = 0.55
    wm_width = int(base.width * scale_factor)
    wm_height = int(wm_width * (watermark.height / watermark.width))
    watermark = watermark.resize((wm_width, wm_height), Image.Resampling.LANCZOS)

    watermark = watermark.rotate(45, expand=True)

    alpha = watermark.getchannel("A")
    alpha = ImageEnhance.Brightness(alpha).enhance(1)  # Adjust opacity here
    watermark.putalpha(alpha)

    transparent_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))

    x = (base.width - watermark.width) // 2
    y = int((base.height - watermark.height) * 0.75)
    transparent_layer.paste(watermark, (x, y), watermark)

    final = Image.alpha_composite(base, transparent_layer)

    buf = BytesIO()
    final.convert("RGB").save(buf, format="JPEG", quality=95)
    buf.seek(0)
    return buf

@app.get("/", response_class=HTMLResponse)
async def form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/watermark", response_class=HTMLResponse)
async def watermark_images(request: Request, files: List[UploadFile] = File(...)):
    images_data = []
    for file in files:
        try:
            watermarked_img_buf = add_watermark_to_image(file.file, WATERMARK_PATH)
            encoded_string = base64.b64encode(watermarked_img_buf.read()).decode("utf-8")
            mime_type = "image/jpeg"
            images_data.append({
                "filename": file.filename,
                "data": f"data:{mime_type};base64,{encoded_string}"
            })
        except Exception as e:
            print(f"Failed processing {file.filename}: {e}")

    return templates.TemplateResponse("result.html", {"request": request, "images": images_data})
