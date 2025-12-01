import os
import json
import uuid
import requests
from openai import OpenAI
from fastapi import UploadFile, HTTPException

# ایمپورت مدل‌ها (مسیرها را طبق ساختار پروژه خود چک کنید)
from models.history import PlantHistory
from models.user import User
# فرض بر این است که مدل UserGarden در فایلی مثل models/garden.py است
from models.garden import UserGarden

# تنظیمات
UPLOAD_DIR = "static/uploads/plants"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
        شناسایی گیاه، ذخیره در تاریخچه و بررسی حضور در باغچه کاربر.
        """

        # 1. خواندن و ذخیره فایل
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

        # --- 2. ارسال به PlantNet ---
        try:
            files = [('images', (image_file.filename, image_content, image_file.content_type))]
            data = {'organs': 'auto'}

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
            if os.path.exists(file_path):
                os.remove(file_path)
            raise he
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            print(f"PlantNet Error: {e}")
            raise HTTPException(status_code=500, detail="خطای سرور در شناسایی گیاه")

        # --- 3. بررسی: آیا اطلاعات این گیاه قبلاً در دیتابیس موجود است؟ ---
        try:
            existing_record = await PlantHistory.filter(
                common_name=common_name_fa
            ).first()

            if existing_record:
                # نکته مهم: اگر اینجا فایل جدید را پاک کنید، تاریخچه کاربر جدید عکس نخواهد داشت.
                # بهتر است فایل را نگه دارید تا هر کاربر عکس اسکن شده خودش را ببیند.
                # اما اگر می‌خواهید در فضای سرور صرفه‌جویی کنید، باید از عکس رکورد قدیمی استفاده کنید:

                final_image_url = saved_image_url
                # اگر میخواهید فایل جدید پاک شود و از عکس قبلی استفاده شود، این بخش را از کامنت درآورید:
                # if os.path.exists(file_path):
                #     os.remove(file_path)
                # final_image_url = existing_record.image_path

                # ثبت تاریخچه جدید
                new_record = await PlantHistory.create(
                    user=user,
                    image_path=final_image_url,
                    plant_name=existing_record.plant_name,
                    common_name=existing_record.common_name,
                    accuracy=existing_record.accuracy,
                    description=existing_record.description,
                    details=existing_record.details
                )

                # ++++++ بررسی وضعیت باغچه (in_garden) ++++++
                # چک می‌کنیم آیا کاربری که درخواست داده، این گیاه (با نام علمی یکسان) را در باغچه دارد؟
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
                    "image_url": final_image_url,
                    "description": existing_record.description,
                    "in_garden": is_in_garden,  # <--- فلگ اضافه شد
                    **(existing_record.details or {})
                }

        except Exception as e:
            print(f"Database Check Error: {e}")

        # --- 4. اگر گیاه جدید است: دریافت اطلاعات از GPT ---
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

            content_str = chat_response.choices[0].message.content
            care_info = json.loads(content_str)

        except Exception as e:
            print(f"LLM Error: {e}")
            care_info = {"description": "اطلاعات تکمیلی دریافت نشد."}

        # --- 5. ذخیره رکورد جدید ---
        history_id = None
        try:
            history_record = await PlantHistory.create(
                user=user,
                image_path=saved_image_url,
                plant_name=scientific_name,
                common_name=common_name_fa,
                accuracy=accuracy,
                description=care_info.get('description', ''),
                details=care_info
            )
            history_id = history_record.id
        except Exception as e:
            print(f"Database Save Error: {e}")

        # ++++++ بررسی وضعیت باغچه (in_garden) برای گیاه جدید ++++++
        # ممکن است کاربر قبلا این گیاه را داشته ولی در هیستوری نبوده (یا هیستوری پاک شده)
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
            "in_garden": is_in_garden,  # <--- فلگ اضافه شد
            **care_info
        }
