import json
import requests
from openai import OpenAI
from fastapi import UploadFile, HTTPException

# تنظیمات PlantNet
PLANTNET_API_KEY = "2b10f4guWVb5SSBwfWVRv9Na8e"
PLANTNET_PROJECT = "all"
PLANTNET_URL = f"https://my-api.plantnet.org/v2/identify/{PLANTNET_PROJECT}?api-key={PLANTNET_API_KEY}&lang=fa"

# تنظیمات GapGPT
client = OpenAI(
    base_url='https://api.gapgpt.app/v1',
    api_key='sk-W9TNjsPN32u1XpuDTKB1AxMV5YhYZhYGljk9Go2bqzpQPCEP'
)


class PlantIdentifierService:

    @staticmethod
    async def identify_and_analyze(image_file: UploadFile):
        # --- الف) شناسایی با PlantNet (کد قبلی شما) ---
        image_content = await image_file.read()
        await image_file.seek(0)
        files = [('images', (image_file.filename, image_content, image_file.content_type))]
        data = {'organs': 'auto'}

        scientific_name = ""
        common_name_fa = ""
        accuracy = 0.0
        reference_image = ""

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
            if best_match.get('images'):
                reference_image = best_match['images'][0]['url'].get('m', '')

        except HTTPException as he:
            raise he
        except Exception as e:
            print(f"PlantNet Error: {e}")
            raise HTTPException(status_code=500, detail="خطای سرور در شناسایی گیاه")

        # --- ب) دریافت اطلاعات ساختاریافته از GPT ---
        care_info = {}
        try:
            # پرامپت جدید: درخواست خروجی JSON دقیق
            prompt = (
                f"من گیاهی با نام علمی '{scientific_name}' (نام فارسی: {common_name_fa}) دارم. "
                "لطفاً خروجی را دقیقاً و فقط به صورت یک JSON معتبر (بدون هیچ متن اضافه) با فیلدهای زیر تولید کن:\n"
                "{\n"
                "  \"description\": \"توضیحات کلی کوتاه (حداکثر ۳ خط)\",\n"
                "  \"water\": \"خلاصه آبیاری (مثلاً: ۳ روز - ۵ روز)\",\n"
                "  \"water_detail\": \"توضیح کامل نحوه آبیاری\",\n"
                "  \"light\": \"میزان نور (مثلاً: ۴۰۰ - ۱۵۰۰ لوکس)\",\n"
                "  \"light_detail\": \"توضیح کامل نور مناسب\",\n"
                "  \"temp\": \"دمای مناسب (مثلاً: ۱۰°C - ۲۵°C)\",\n"
                "  \"fertilizer\": \"کود مناسب (مثلاً: کود ۲۰-۲۰-۲۰)\",\n"
                "  \"difficulty\": \"سختی نگهداری (مثلاً: ۳/۵)\",\n"
                "  \"toxicity\": \"آیا سمی است؟ توضیح کوتاه\"\n"
                "}"
                "زبان تمام مقادیر فارسی باشد."
            )

            chat_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "تو یک گیاه‌پزشک متخصص هستی که خروجی JSON تولید می‌کند."},
                    {"role": "user", "content": prompt}
                ],
                # اگر API پشتیبانی کند این خط عالی است، اگر نه خود پرامپت کافیست
                response_format={"type": "json_object"}
            )

            content_str = chat_response.choices[0].message.content
            # تمیزکاری جیسون در صورتی که مدل متن اضافه فرستاده باشد
            start = content_str.find('{')
            end = content_str.rfind('}') + 1
            if start != -1 and end != -1:
                care_info = json.loads(content_str[start:end])
            else:
                care_info = {"description": content_str}  # فال‌بک

        except Exception as e:
            print(f"LLM Error: {e}")
            care_info = {"description": "اطلاعات تکمیلی دریافت نشد."}

        # --- ج) بازگشت نتیجه نهایی ---
        return {
            "status": "success",
            "plant_name": scientific_name,
            "common_name": common_name_fa,
            "accuracy": accuracy,
            "image_url": reference_image,
            # ادغام دیکشنری اطلاعات نگهداری در پاسخ اصلی
            **care_info
        }
