import os
import json
import uuid
import requests
from datetime import datetime
from tortoise.expressions import Q

from openai import OpenAI
from fastapi import UploadFile, HTTPException

# مدل‌ها
from models.history import PlantHistory
from models.user import User
from models.garden import UserGarden

# تنظیمات
UPLOAD_DIR = "static/uploads/plants"
os.makedirs(UPLOAD_DIR, exist_ok=True)

PLANTNET_API_KEY = "2b10f4guWVb5SSBwfWVRv9Na8e"
PLANTNET_PROJECT = "all"
PLANTNET_URL = f"https://my-api.plantnet.org/v2/identify/{PLANTNET_PROJECT}?api-key={PLANTNET_API_KEY}&lang=fa"

client = OpenAI(
    base_url="https://api.gapgpt.app/v1",
    api_key="sk-W9TNjsPN32u1XpuDTKB1AxMV5YhYZhYGljk9Go2bqzpQPCEP"
)


class PlantIdentifierService:

    @staticmethod
    async def identify_and_analyze(image_file: UploadFile, user: User):
        """
        شناسایی گیاه، مدیریت هوشمند تاریخچه کاربر و بررسی حضور در باغچه.

        منطق جدید:
        ۱. گیاه توسط PlantNet شناسایی می‌شود.
        ۲. بررسی می‌شود که آیا **همین کاربر** قبلاً **همین گیاه** را در تاریخچه خود ثبت کرده است یا خیر.
           - اگر بله (revisited): رکورد جدیدی ساخته نمی‌شود. فقط عکس رکورد قبلی آپدیت شده و همان اطلاعات بازگردانده می‌شود.
           - اگر نه (new for user):
             - بررسی می‌شود آیا اطلاعات عمومی این گیاه در سیستم (توسط کاربر دیگری) کش شده است؟
               - اگر بله: از اطلاعات کش‌شده استفاده می‌شود.
               - اگر نه: اطلاعات از سرویس GPT استعلام می‌شود.
             - در نهایت یک رکورد جدید **برای اولین بار** برای این کاربر و این گیاه در تاریخچه ثبت می‌شود.
        """

        # 1. ذخیره فایل آپلود شده
        image_content = await image_file.read()
        file_extension = image_file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        with open(file_path, "wb") as buffer:
            buffer.write(image_content)

        saved_image_url = f"/static/uploads/plants/{unique_filename}"

        scientific_name = ""
        common_name_fa = ""
        accuracy = 0.0

        # ---------------------------------------
        # 2. شناسایی گیاه با PlantNet
        # ---------------------------------------
        try:
            files = [('images', (image_file.filename, image_content, image_file.content_type))]
            data = {'organs': 'auto'}

            req = requests.Request('POST', url=PLANTNET_URL, files=files, data=data)
            prepared = req.prepare()
            session = requests.Session()
            response = session.send(prepared)

            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="گیاهی شناسایی نشد.")
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="خطا در سرویس شناسایی گیاه.")

            json_result = response.json()
            if not json_result.get("results"):
                raise HTTPException(status_code=404, detail="هیچ گیاهی با این تصویر پیدا نشد.")

            best_match = json_result["results"][0]
            scientific_name = best_match["species"]["scientificNameWithoutAuthor"]
            common_names = best_match["species"].get("commonNames", [])
            common_name_fa = common_names[0] if common_names else scientific_name
            accuracy = round(best_match["score"] * 100, 1)

        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            if isinstance(e, HTTPException):
                raise e
            print(f"PlantNet Error: {e}")
            raise HTTPException(status_code=500, detail="خطای سرور در ارتباط با سرویس شناسایی گیاه.")

        # -------------------------------------------------------------------
        # 3. بررسی تاریخچه *همین کاربر* برای *همین گیاه*
        # -------------------------------------------------------------------
        existing_user_history = await PlantHistory.filter(
            user=user,
            plant_name=scientific_name
        ).first()

        # اگر کاربر قبلاً این گیاه را اسکن کرده باشد، رکورد جدید نمی‌سازیم
        if existing_user_history:
            # عکس جدید را جایگزین عکس قبلی در تاریخچه می‌کنیم
            old_image_path = existing_user_history.image_path.lstrip('/')
            if os.path.exists(old_image_path):
                os.remove(old_image_path)
            existing_user_history.image_path = saved_image_url
            existing_user_history.accuracy = accuracy  # دقت شناسایی جدید را ثبت می‌کنیم
            existing_user_history.created_at = datetime.utcnow()  # زمان اسکن را به‌روز می‌کنیم
            await existing_user_history.save()

            is_in_garden = await UserGarden.filter(
                user=user,
                plant_name=scientific_name
            ).exists()

            return {
                "status": "revisited",  # وضعیت جدید برای اعلام اینکه این گیاه قبلاً در تاریخچه بوده
                "history_id": existing_user_history.id,
                "plant_name": existing_user_history.plant_name,
                "common_name": existing_user_history.common_name,
                "accuracy": accuracy,
                "image_url": saved_image_url,
                "in_garden": is_in_garden,
                "description": existing_user_history.description,
                **(existing_user_history.details or {})
            }

        # -------------------------------------------------------------------
        # 4. اگر برای کاربر جدید است، اطلاعات را آماده می‌کنیم (با استفاده از کش یا GPT)
        # -------------------------------------------------------------------
        care_info = {}
        description = ""

        # ابتدا بررسی می‌کنیم آیا اطلاعات عمومی این گیاه قبلاً توسط کاربر دیگری ذخیره شده (کش)
        cached_plant_info = await PlantHistory.filter(plant_name=scientific_name, details__isnull=False).first()

        if cached_plant_info:
            # اطلاعات عمومی گیاه از قبل وجود دارد، از آن استفاده کن
            care_info = cached_plant_info.details
            description = cached_plant_info.description
            if not common_name_fa or common_name_fa == scientific_name:
                common_name_fa = care_info.get("name_fa", common_name_fa)
        else:
            # اطلاعات وجود ندارد، از GPT بگیر
            try:
                prompt = (
                    f"من گیاهی با نام علمی '{scientific_name}' (نام فارسی: {common_name_fa}) دارم. "
                    "لطفاً خروجی را دقیقاً و فقط به صورت یک JSON معتبر با فیلدهای زیر تولید کن:\n"
                    "{\n"
                    "  \"name_fa\": \"اسم فارسی گیاه\",\n"
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
                        {"role": "system", "content": "تو یک گیاه‌پزشک متخصص هستی که فقط با فرمت JSON پاسخ می‌دهی."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )

                content = chat_response.choices[0].message.content
                care_info = json.loads(content)
                description = care_info.get("description", "")
                if not common_name_fa or common_name_fa == scientific_name:
                    common_name_fa = care_info.get("name_fa", common_name_fa)

            except Exception as e:
                print(f"LLM Error: {e}")
                care_info = {}
                description = "اطلاعات تکمیلی در حال حاضر در دسترس نیست."

        # -------------------------------------------------
        # 5. ذخیره رکورد جدید برای اولین بار برای این کاربر
        # -------------------------------------------------
        new_history_record = await PlantHistory.create(
            user=user,
            image_path=saved_image_url,
            plant_name=scientific_name,
            common_name=common_name_fa,
            accuracy=accuracy,
            description=description,
            details=care_info if care_info else None
        )

        return {
            "status": "success",
            "history_id": new_history_record.id,
            "plant_name": scientific_name,
            "common_name": common_name_fa,
            "accuracy": accuracy,
            "image_url": saved_image_url,
            "in_garden": False,
            **(care_info or {})
        }
