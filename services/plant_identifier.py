import os
import json
import shutil
import uuid
import requests
from datetime import datetime
from openai import OpenAI
from fastapi import UploadFile, HTTPException

from models.history import PlantHistory
from models.user import User

# تنظیمات پوشه ذخیره عکس‌ها
UPLOAD_DIR = "static/uploads/plants"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# تنظیمات API
PLANTNET_API_KEY = "2b10f4guWVb5SSBwfWVRv9Na8e"
PLANTNET_PROJECT = "all"
PLANTNET_URL = f"https://my-api.plantnet.org/v2/identify/{PLANTNET_PROJECT}?api-key={PLANTNET_API_KEY}&lang=fa"

client = OpenAI(
    base_url='https://api.gapgpt.app/v1',
    api_key='sk-W9TNjsPN32u1XpuDTKB1AxMV5YhYZhYGljk9Go2bqzpQPCEP'
)


class PlantIdentifierService:

    @staticmethod
    async def identify_and_analyze(image_file: UploadFile, user: User):
        """
        این متد علاوه بر شناسایی، عکس و نتیجه را در دیتابیس برای کاربر ذخیره می‌کند.
        """

        # 1. خواندن فایل یکبار برای همیشه
        image_content = await image_file.read()

        # 2. ذخیره فایل روی دیسک (برای دسترسی بعدی)
        file_extension = image_file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        with open(file_path, "wb") as buffer:
            buffer.write(image_content)

        # ساخت URL نسبی برای ذخیره در دیتابیس (فرض بر این است که static را mount کرده‌اید)
        saved_image_url = f"/static/uploads/plants/{unique_filename}"

        # 3. آماده‌سازی برای PlantNet
        # نشانگر فایل را به اول برمی‌گردانیم یا از محتوای خوانده شده استفاده می‌کنیم
        files = [('images', (image_file.filename, image_content, image_file.content_type))]
        data = {'organs': 'auto'}

        scientific_name = ""
        common_name_fa = ""
        accuracy = 0.0
        # reference_image برای عکس مرجع خود plantnet است، اما ما عکس کاربر را هم داریم

        # --- ارسال به PlantNet ---
        try:
            req = requests.Request('POST', url=PLANTNET_URL, files=files, data=data)
            prepared = req.prepare()
            s = requests.Session()
            response = s.send(prepared)

            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="گیاهی شناسایی نشد.")
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="خطا در سرویس PlantNet")

            json_result = response.json()
            if not json_result.get('results'):
                raise HTTPException(status_code=404, detail="هیچ گیاهی پیدا نشد.")

            best_match = json_result['results'][0]
            scientific_name = best_match['species']['scientificNameWithoutAuthor']
            common_names = best_match['species'].get('commonNames', [])
            common_name_fa = common_names[0] if common_names else scientific_name
            accuracy = round(best_match['score'] * 100, 1)

        except HTTPException as he:
            raise he
        except Exception as e:
            print(f"PlantNet Error: {e}")
            raise HTTPException(status_code=500, detail="خطای سرور در شناسایی گیاه")

        # --- ارسال به GPT برای اطلاعات نگهداری ---
        care_info = {}
        try:
            prompt = (
                f"من گیاهی با نام علمی '{scientific_name}' (نام فارسی: {common_name_fa}) دارم. "
                "لطفاً خروجی را دقیقاً و فقط به صورت یک JSON معتبر با فیلدهای زیر تولید کن:\n"
                "{\n"
                "  \"description\": \"توضیحات کلی کوتاه (حداکثر ۳ خط)\",\n"
                "  \"water\": \"خلاصه آبیاری\",\n"
                "  \"water_detail\": \"توضیح کامل نحوه آبیاری\",\n"
                "  \"light\": \"میزان نور\",\n"
                "  \"light_detail\": \"توضیح کامل نور مناسب\",\n"
                "  \"temp\": \"دمای مناسب\",\n"
                "  \"fertilizer\": \"کود مناسب\",\n"
                "  \"difficulty\": \"سختی نگهداری\",\n"
                "  \"toxicity\": \"وضعیت سمی بودن\"\n"
                "}"
                "زبان تمام مقادیر فارسی باشد."
            )

            chat_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "تو یک گیاه‌پزشک متخصص هستی."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            content_str = chat_response.choices[0].message.content
            care_info = json.loads(content_str)

        except Exception as e:
            print(f"LLM Error: {e}")
            care_info = {"description": "اطلاعات تکمیلی دریافت نشد."}

        # --- 4. ذخیره در دیتابیس (بخش جدید) ---
        try:
            await PlantHistory.create(
                user=user,
                image_path=saved_image_url,  # آدرس عکس آپلودی کاربر
                plant_name=scientific_name,
                common_name=common_name_fa,
                accuracy=accuracy,
                description=care_info.get('description', ''),
                details=care_info  # ذخیره کل جیسون نگهداری
            )
        except Exception as e:
            print(f"Database Save Error: {e}")
            # اگر ذخیره در دیتابیس خطا داد، پروسه را متوقف نمی‌کنیم، فقط لاگ می‌زنیم

        # --- بازگشت نتیجه به کاربر ---
        return {
            "status": "success",
            "plant_name": scientific_name,
            "common_name": common_name_fa,
            "accuracy": accuracy,
            "image_url": saved_image_url,  # برای نمایش در اپلیکیشن
            **care_info
        }
