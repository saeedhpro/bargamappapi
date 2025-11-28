import requests
from openai import OpenAI
from fastapi import UploadFile, HTTPException

# تنظیمات PlantNet
PLANTNET_API_KEY = "2b10f4guWVb5SSBwfWVRv9Na8e"
PLANTNET_PROJECT = "all"  # یا "kt" برای فلور جهانی (all بهتر است)
PLANTNET_URL = f"https://my-api.plantnet.org/v2/identify/{PLANTNET_PROJECT}?api-key={PLANTNET_API_KEY}&lang=fa"

# تنظیمات GapGPT
client = OpenAI(
    base_url='https://api.gapgpt.app/v1',
    api_key='sk-W9TNjsPN32u1XpuDTKB1AxMV5YhYZhYGljk9Go2bqzpQPCEP'
)


class PlantIdentifierService:

    @staticmethod
    async def identify_and_analyze(image_file: UploadFile):
        # --- الف) آماده‌سازی تصویر برای PlantNet ---
        image_content = await image_file.read()

        # بازگرداندن نشانگر فایل به ابتدا (برای احتیاط)
        await image_file.seek(0)

        # نکته مهم: استفاده از فرمت صحیح تاپل برای multipart
        # ('field_name', ('filename', content, 'mime_type'))
        files = [
            ('images', (image_file.filename, image_content, image_file.content_type))
        ]

        # ارسال organs به صورتی که PlantNet بفهمد
        data = {
            'organs': 'auto'  # اغلب رشته تکی 'auto' بهتر از لیست ['auto'] در requests عمل می‌کند
        }

        scientific_name = ""
        common_name_fa = ""
        accuracy = 0.0
        reference_image = ""

        # --- ب) ارسال درخواست به PlantNet ---
        try:
            req = requests.Request('POST', url=PLANTNET_URL, files=files, data=data)
            prepared = req.prepare()
            s = requests.Session()
            response = s.send(prepared)

            # --- مدیریت خطاها ---

            # ۱. اگر گیاه پیدا نشد (خطای ۴۰۴ معروف PlantNet)
            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="گیاهی در تصویر شناسایی نشد. لطفاً عکسی واضح‌تر یا از زاویه‌ای دیگر بگیرید."
                )

            # ۲. سایر خطاهای PlantNet
            if response.status_code != 200:
                print(f"PlantNet API Error: {response.text}")
                raise HTTPException(
                    status_code=400,
                    detail="خطا در ارتباط با سرویس شناسایی گیاه."
                )

            json_result = response.json()

            # ۳. بررسی وجود نتایج در JSON
            if not json_result.get('results') or len(json_result['results']) == 0:
                raise HTTPException(status_code=404, detail="هیچ گیاهی با قطعیت کافی شناسایی نشد.")

            # استخراج بهترین نتیجه
            best_match = json_result['results'][0]
            scientific_name = best_match['species']['scientificNameWithoutAuthor']

            # تلاش برای یافتن نام فارسی یا استفاده از نام علمی
            common_names = best_match['species'].get('commonNames', [])
            common_name_fa = common_names[0] if common_names else scientific_name

            accuracy = round(best_match['score'] * 100, 1)

            # تصویر مرجع
            if best_match.get('images') and len(best_match['images']) > 0:
                reference_image = best_match['images'][0]['url'].get('m', '')

        except HTTPException as he:
            raise he
        except Exception as e:
            print(f"Internal Processing Error: {e}")
            raise HTTPException(status_code=500, detail="خطای داخلی سرور هنگام پردازش تصویر.")

        # --- ج) ارسال به هوش مصنوعی (فقط در صورت شناسایی موفق) ---
        ai_description = ""
        try:
            prompt = (
                f"من گیاهی با نام علمی '{scientific_name}' (نام رایج: {common_name_fa}) دارم. "
                "لطفاً به زبان فارسی، خلاصه و مفید (حداکثر ۱۵۰ کلمه) اطلاعات زیر را بنویس:\n"
                "۱. معرفی کوتاه\n"
                "۲. نور مورد نیاز\n"
                "۳. آبیاری\n"
                "۴. آیا برای حیوانات خانگی سمی است؟"
            )

            chat_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "تو یک گیاه‌پزشک و متخصص کشاورزی هستی."},
                    {"role": "user", "content": prompt}
                ]
            )
            ai_description = chat_response.choices[0].message.content

        except Exception as e:
            print(f"LLM Error: {e}")
            ai_description = "شناسایی نام گیاه موفقیت‌آمیز بود، اما دریافت توضیحات تکمیلی با خطا مواجه شد."

        return {
            "status": "success",
            "plant_name": scientific_name,
            "common_name": common_name_fa,
            "accuracy": accuracy,
            "description": ai_description,
            "image_url": reference_image
        }
