import os
import json
import uuid
import requests
from datetime import datetime
import base64
import traceback

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
    async def identify_and_analyze_old(image_file: UploadFile, user: User):
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
            common_name_fa = common_names[0] if common_names else None
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
            plant_name=scientific_name
        ).first()

        # اگر کاربر قبلاً این گیاه را اسکن کرده باشد، رکورد جدید نمی‌سازیم
        # اگر کاربر قبلاً این گیاه را اسکن کرده باشد، رکورد جدید نمی‌سازیم
        if existing_user_history:

            # --- ۱. افزودن عکس جدید به image_paths ---
            image_paths = existing_user_history.image_paths or []

            # --- ۱. image_path اصلی را تغییر نمی‌دهیم، فقط اگر خالی بود یکبار ست می‌شود ---
            if not existing_user_history.image_path:
                existing_user_history.image_path = saved_image_url
            else:
                # افزودن عکس جدید به لیست
                image_paths.append(saved_image_url)
                existing_user_history.image_paths = image_paths

            # --- ۳. دقت و زمان به‌روزرسانی شود ---
            existing_user_history.accuracy = accuracy
            existing_user_history.created_at = datetime.utcnow()

            await existing_user_history.save()

            # ---- بررسی حضور در باغچه ----
            is_in_garden = await UserGarden.filter(
                user=user,
                plant_name=scientific_name
            ).exists()

            return {
                "status": "revisited",
                "history_id": existing_user_history.id,
                "plant_name": existing_user_history.plant_name,
                "common_name": existing_user_history.common_name,
                "accuracy": accuracy,
                "image_url": saved_image_url,  # عکس جدید
                "image_paths": image_paths,  # همه عکس‌ها
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
        else:
            # اطلاعات وجود ندارد، از GPT بگیر
            try:
                prompt = (
                    f"گیاهی با نام علمی '{scientific_name}' دارم. "
                    "لطفاً نام فارسی این گیاه را نیز تعیین کن.\n\n"
                    "قوانین تعیین نام فارسی:\n"
                    "1) اگر این گونه (species) نام رسمی فارسی دارد → همان را بده.\n"
                    "2) اگر نام رسمی ندارد، از اطلاعات معتبر دربارهٔ مبدأ گیاه یک نام غیررسمی بساز "
                    "(مثلاً گیاهان چینی → «... چینی»، ژاپنی → «... ژاپنی»، ایرانی → «... ایرانی»).\n"
                    "۳) ترجمه ماشینی یا ساختن نام جعلی ممنوع است.\n"
                    "۴) اگر نام معتبر پیدا نکردی، مقدار آن باید رشتهٔ خالی باشد («»).\n\n"
                    "خروجی را فقط و فقط یک JSON معتبر با ساختار زیر برگردان:\n"
                    "{\n"
                    "  \"common_name_fa\": \"نام فارسی رسمی یا غیررسمی\",\n"
                    "  \"description\": \"توضیحات کوتاه (حداکثر ۳ خط)\",\n"
                    "  \"water\": \"خلاصه آبیاری\",\n"
                    "  \"water_detail\": \"توضیح کامل نحوه آبیاری\",\n"
                    "  \"light\": \"میزان نور\",\n"
                    "  \"light_detail\": \"توضیح کامل نور مناسب\",\n"
                    "  \"temp\": \"دمای مناسب\",\n"
                    "  \"fertilizer\": \"کود مناسب\",\n"
                    "  \"difficulty\": \"سختی نگهداری\",\n"
                    "  \"toxicity\": \"وضعیت سمی بودن\"\n"
                    "}\n"
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
                print(common_name_fa)
                description = care_info.get("description", "")
                if common_name_fa is None or common_name_fa == "":
                    common_name_fa = care_info.get("common_name_fa", "")
                if common_name_fa is None or common_name_fa == "":
                    common_name_fa = care_info.get("common_name", "")
                print(common_name_fa, "1")
            except Exception as e:
                print(f"LLM Error: {e}")
                care_info = {}
                description = "اطلاعات تکمیلی در حال حاضر در دسترس نیست."

        # -------------------------------------------------
        # 5. ذخیره رکورد جدید برای اولین بار برای این کاربر
        # -------------------------------------------------
        image_paths = []
        new_history_record = await PlantHistory.create(
            user=user,
            image_path=saved_image_url,
            plant_name=scientific_name,
            common_name=common_name_fa,
            image_paths=image_paths,
            accuracy=accuracy,
            description=description,
            details=care_info if care_info else None
        )
        response = {
            **(care_info or {}),
            "status": "success",
            "history_id": new_history_record.id,
            "plant_name": scientific_name,
            "common_name": common_name_fa,
            "image_paths": image_paths,
            "accuracy": accuracy,
            "image_url": saved_image_url,
            "in_garden": False,
        }
        print(response)
        return response

    # ----------------------------------------------------------------------
    # نسخه جدید (ChatGPT Vision)  ←  این نسخه فعال است
    # ----------------------------------------------------------------------
    @staticmethod
    async def identify_and_analyze(image_file: UploadFile, user: User):

        print("\n\n[IDENTIFY] --- Start identify_and_analyze ---")
        print(f"[IDENTIFY] User: {user.id}")
        print(f"[IDENTIFY] Filename: {image_file.filename}")

        # ---------------------------------------------------------------
        # 1) ذخیره فایل در سرور
        # ---------------------------------------------------------------
        try:
            image_content = await image_file.read()
            print(f"[IDENTIFY] Image content size: {len(image_content)} bytes")
        except Exception as e:
            print("[IDENTIFY] ERROR reading file:", e)
            traceback.print_exc()
            raise

        ext = image_file.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        try:
            with open(file_path, "wb") as f:
                f.write(image_content)
            print(f"[IDENTIFY] Saved image to: {file_path}")
        except Exception as e:
            print("[IDENTIFY] ERROR saving file:", e)
            traceback.print_exc()
            raise

        saved_image_url = f"/static/uploads/plants/{filename}"
        print(f"[IDENTIFY] Saved image URL: {saved_image_url}")

        # Base64 برای GPT Vision
        try:
            image_base64 = base64.b64encode(image_content).decode("utf-8")
            print("[IDENTIFY] Base64 encode success")
        except Exception as e:
            print("[IDENTIFY] ERROR base64:", e)
            traceback.print_exc()
            raise

        data_url = f"data:{image_file.content_type};base64,{image_base64}"
        print("[IDENTIFY] Created data_url")

        # ---------------------------------------------------------------
        # 2) ارسال عکس به ChatGPT برای تشخیص گیاه
        # ---------------------------------------------------------------
        print("[IDENTIFY] Calling GPT Vision...")

        try:
            prompt = (
                "این تصویر یک گیاه است. لطفاً آن را دقیق تحلیل کن و فقط و فقط JSON زیر را بده:\n"
                "{\n"
                "  \"scientific_name\": \"نام علمی دقیق\",\n"
                "  \"common_name\": \"نام رایج لاتین\",\n"
                "  \"common_name_fa\": \"نام فارسی اگر موجود بود\",\n"
                "  \"confidence\": عدد بین 0 تا 100,\n"
                "  \"description\": \"توضیح کوتاه\",\n"
                "  \"water\": \"خلاصه آبیاری\",\n"
                "  \"water_detail\": \"توضیح کامل آبیاری\",\n"
                "  \"light\": \"نور مناسب\",\n"
                "  \"light_detail\": \"توضیح کامل نور\",\n"
                "  \"temp\": \"دمای مناسب\",\n"
                "  \"fertilizer\": \"کود مناسب\",\n"
                "  \"difficulty\": \"درجه سختی نگهداری\"\n"
                "}\n"
                "فقط JSON بده."
            )

            # ❗ اصلاح مهم: input_text → text
            chat_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": data_url
                                },
                            },
                        ],
                    }
                ],
                response_format={"type": "json_object"},
            )

            print("[IDENTIFY] GPT Response received.")
            print("[IDENTIFY] Raw response object:", chat_response)

            raw_content = chat_response.choices[0].message.content
            print("[IDENTIFY] Raw content:", raw_content)

            info = json.loads(raw_content)
            print("[IDENTIFY] JSON parsed successfully")

            scientific_name = info.get("scientific_name", "").strip()
            common_name_fa = info.get("common_name_fa", "") or ""
            accuracy = info.get("confidence", 65)

            print(f"[IDENTIFY] Parsed scientific_name: {scientific_name}")
            print(f"[IDENTIFY] accuracy: {accuracy}")

            care_info = {k: v for k, v in info.items() if k not in ["scientific_name", "confidence"]}
            description = info.get("description", "")

        except Exception as e:
            print("\n[IDENTIFY] --- GPT Vision Error ---")
            print("[IDENTIFY] Exception:", e)
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"GPT Vision Error: {str(e)}")

        if not scientific_name:
            print("[IDENTIFY] No scientific name returned by GPT")
            raise HTTPException(status_code=404, detail="مدل نتوانست گیاه را شناسایی کند.")

        # ---------------------------------------------------------------
        # 3) بررسی revisited
        # ---------------------------------------------------------------
        print("[IDENTIFY] Checking revisited...")

        existing_user_history = await PlantHistory.filter(
            user=user,
            plant_name=scientific_name,
        ).first()

        if existing_user_history:
            print("[IDENTIFY] revisited: existing record found:", existing_user_history.id)

            image_paths = existing_user_history.image_paths or []
            image_paths.append(saved_image_url)

            existing_user_history.image_paths = image_paths
            existing_user_history.accuracy = accuracy
            existing_user_history.created_at = datetime.utcnow()

            if not existing_user_history.image_path:
                existing_user_history.image_path = saved_image_url

            await existing_user_history.save()

            is_in_garden = await UserGarden.filter(user=user, plant_name=scientific_name).exists()

            print("[IDENTIFY] revisited complete.")
            return {
                "status": "revisited",
                "history_id": existing_user_history.id,
                "plant_name": scientific_name,
                "common_name": common_name_fa,
                "common_name_fa": common_name_fa,
                "image_url": saved_image_url,
                "image_paths": image_paths,
                "accuracy": accuracy,
                "description": existing_user_history.description,
                "in_garden": is_in_garden,
                **(existing_user_history.details or {}),
            }

        # ---------------------------------------------------------------
        # 4) استفاده از کش عمومی
        # ---------------------------------------------------------------
        print("[IDENTIFY] Checking cached data...")
        cached = await PlantHistory.filter(
            plant_name=scientific_name,
            details__isnull=False
        ).first()

        if cached:
            print("[IDENTIFY] Cache hit:", cached.id)
            care_info = cached.details
            description = cached.description
        else:
            print("[IDENTIFY] No cached data.")

        # ---------------------------------------------------------------
        # 5) ثبت رکورد جدید
        # ---------------------------------------------------------------
        print("[IDENTIFY] Creating new history record...")

        new_history = await PlantHistory.create(
            user=user,
            image_path=saved_image_url,
            plant_name=scientific_name,
            common_name=common_name_fa,
            image_paths=[],
            accuracy=accuracy,
            description=description,
            details=care_info or None,
        )

        print("[IDENTIFY] New record created:", new_history.id)

        return {
            "status": "success",
            "history_id": new_history.id,
            "plant_name": scientific_name,
            "common_name": common_name_fa,
            "common_name_fa": common_name_fa,
            "image_url": saved_image_url,
            "image_paths": [],
            "accuracy": accuracy,
            "description": description,
            "in_garden": False,
            **(care_info or {}),
        }