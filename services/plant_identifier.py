import os
import json
import uuid
import requests
from datetime import datetime, timedelta
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
        شناسایی گیاه، ذخیره در تاریخچه و بررسی حضور در باغچه کاربر.
        """

        # 1. ذخیره فایل
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
        # 2. درخواست PlantNet
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
                raise HTTPException(status_code=400, detail="خطا در سرویس PlantNet")

            json_result = response.json()
            if not json_result.get("results"):
                raise HTTPException(status_code=404, detail="هیچ گیاهی پیدا نشد.")

            best_match = json_result["results"][0]
            scientific_name = best_match["species"]["scientificNameWithoutAuthor"]
            common_names = best_match["species"].get("commonNames", [])
            common_name_fa = common_names[0] if common_names else scientific_name
            accuracy = round(best_match["score"] * 100, 1)

        except HTTPException as he:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise he

        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            print(f"PlantNet Error: {e}")
            raise HTTPException(status_code=500, detail="خطای سرور در شناسایی گیاه")

        # -------------------------------------------------------------------
        # 3. اگر همین گیاه را زیر 1 دقیقه قبل فرستاده بوده → نتیجه قبلی را بده
        # -------------------------------------------------------------------
        try:
            one_minute_ago = datetime.utcnow() - timedelta(seconds=60)

            recent_record = await PlantHistory.filter(
                Q(user=user) &
                Q(plant_name=scientific_name) &
                Q(created_at__gte=one_minute_ago)
            ).first()

            if recent_record:
                is_in_garden = await UserGarden.filter(
                    user=user,
                    plant_name=scientific_name
                ).exists()

                return {
                    "status": "recent",
                    "history_id": recent_record.id,
                    "plant_name": recent_record.plant_name,
                    "common_name": recent_record.common_name,
                    "accuracy": recent_record.accuracy,
                    "image_url": recent_record.image_path,
                    "in_garden": is_in_garden,
                    **(recent_record.details or {})
                }
        except Exception as e:
            print("Recent-check error:", e)

        # -------------------------------------------------
        # 4. بررسی وجود رکورد قدیمی با همین common_name
        # -------------------------------------------------
        try:
            existing_record = await PlantHistory.filter(
                common_name=common_name_fa
            ).first()

            if existing_record:

                new_record = await PlantHistory.create(
                    user=user,
                    image_path=saved_image_url,
                    plant_name=existing_record.plant_name,
                    common_name=existing_record.common_name,
                    accuracy=existing_record.accuracy,
                    description=existing_record.description,
                    details=existing_record.details
                )

                is_in_garden = await UserGarden.filter(
                    user=user,
                    plant_name=existing_record.plant_name
                ).exists()

                return {
                    "status": "existing",
                    "history_id": new_record.id,
                    "plant_name": existing_record.plant_name,
                    "common_name": existing_record.common_name,
                    "accuracy": existing_record.accuracy,
                    "image_url": saved_image_url,
                    "description": existing_record.description,
                    "in_garden": is_in_garden,
                    **(existing_record.details or {})
                }

        except Exception as e:
            print("Existing-check error:", e)

        # -------------------------------------------------
        # 5. دریافت اطلاعات تکمیلی از GPT
        # -------------------------------------------------
        care_info = {}
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
                    {"role": "system", "content": "تو یک گیاه‌پزشک متخصص هستی."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            content = chat_response.choices[0].message.content
            care_info = json.loads(content)

        except Exception as e:
            print("LLM Error:", e)
            care_info = {}

        # -------------------------------------------------
        # 6. ذخیره رکورد جدید (بدون details اگر خالی بود)
        # -------------------------------------------------
        details_value = care_info if care_info else None

        history_id = None
        try:
            history_record = await PlantHistory.create(
                user=user,
                image_path=saved_image_url,
                plant_name=scientific_name,
                common_name=common_name_fa,
                accuracy=accuracy,
                description=care_info.get("description", ""),
                details=details_value
            )
            history_id = history_record.id

        except Exception as e:
            print("Database Save Error:", e)

        # -------------------------------------------------
        # 7. بررسی وضعیت باغچه
        # -------------------------------------------------
        is_in_garden = await UserGarden.filter(
            user=user,
            plant_name=scientific_name
        ).exists()

        return {
            "status": "success",
            "history_id": history_id,
            "plant_name": scientific_name,
            "common_name": common_name_fa,
            "accuracy": accuracy,
            "image_url": saved_image_url,
            "in_garden": is_in_garden,
            **(care_info or {})
        }
