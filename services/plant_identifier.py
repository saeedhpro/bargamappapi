import os
import json
import uuid
import requests
from datetime import datetime

from openai import OpenAI
from fastapi import UploadFile, HTTPException

from models.history import PlantHistory
from models.user import User
from models.garden import UserGarden


UPLOAD_DIR = "static/uploads/plants"
os.makedirs(UPLOAD_DIR, exist_ok=True)

PLANTNET_API_KEY = "2b10f4guWVb5SSBwfWVRv9Na8e"
PLANTNET_PROJECT = "all"
PLANTNET_URL = (
    f"https://my-api.plantnet.org/v2/identify/{PLANTNET_PROJECT}"
    f"?api-key={PLANTNET_API_KEY}&lang=fa"
)

client = OpenAI(
    base_url="https://api.gapgpt.app/v1",
    api_key="sk-W9TNjsPN32u1XpuDTKB1AxMV5YhYZhYGljk9Go2bqzpQPCEP"
)


# -------------------------------------------------------------
#   CLEAN, SAFE PROMPT BUILDER  (بدون Format Specifier Error)
# -------------------------------------------------------------
def build_full_prompt(scientific_name, genus, family, common_names):

    common_names_json = json.dumps(common_names, ensure_ascii=False)
    common_name_fa = common_names[0] if common_names else ""
    return (
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


# -------------------------------------------------------------
#   SERVICE CLASS
# -------------------------------------------------------------
class PlantIdentifierService:

    @staticmethod
    async def identify_and_analyze(image_file: UploadFile, user: User):

        # -------------------------------------------------------------
        # 1. Save Image
        # -------------------------------------------------------------
        image_content = await image_file.read()
        ext = image_file.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        with open(file_path, "wb") as f:
            f.write(image_content)

        saved_image_url = f"/static/uploads/plants/{filename}"

        # Default values
        scientific_name = ""
        common_name_fa = ""
        accuracy = 0.0

        # -------------------------------------------------------------
        # 2. PlantNet Identification
        # -------------------------------------------------------------
        try:
            files = [
                ("images", (image_file.filename, image_content, image_file.content_type))
            ]
            data = {"organs": "auto"}

            req = requests.Request("POST", url=PLANTNET_URL, files=files, data=data)
            prepped = req.prepare()
            session = requests.Session()
            response = session.send(prepped)

            if response.status_code != 200:
                raise HTTPException(500, "خطا در سرویس تشخیص گیاه")

            result = response.json()
            if not result.get("results"):
                raise HTTPException(404, "گیاهی شناسایی نشد.")

            best = result["results"][0]

            scientific_name = best["species"]["scientificNameWithoutAuthor"]
            common_names = best["species"].get("commonNames", [])
            accuracy = round(best["score"] * 100, 1)

            genus = best["species"]["genus"]["scientificName"]
            family = best["species"]["family"]["scientificName"]

            if common_names:
                common_name_fa = common_names[0]

        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(500, "خطا در شناسایی گیاه.")

        # -------------------------------------------------------------
        # 3. Revisited Case
        # -------------------------------------------------------------
        old = await PlantHistory.filter(user=user, plant_name=scientific_name).first()

        if old:
            paths = old.image_paths or []

            if old.image_path:
                paths.append(saved_image_url)
            else:
                old.image_path = saved_image_url

            old.image_paths = paths
            old.accuracy = accuracy
            old.created_at = datetime.utcnow()
            await old.save()

            in_garden = await UserGarden.filter(
                user=user, plant_name=scientific_name
            ).exists()

            return {
                "status": "revisited",
                "history_id": old.id,
                "plant_name": scientific_name,
                "common_name_fa": old.common_name,
                "accuracy": accuracy,
                "image_url": saved_image_url,
                "image_paths": paths,
                "in_garden": in_garden,
                **(old.details or {}),
            }

        # -------------------------------------------------------------
        # 4. GPT: Naming + Care Info
        # -------------------------------------------------------------
        prompt = build_full_prompt(
            scientific_name=scientific_name,
            genus=genus,
            family=family,
            common_names=common_names
        )

        try:
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "فقط JSON خروجی بده."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            care = json.loads(resp.choices[0].message.content)
            common_name_fa = (
                care.get("common_name_fa") or common_name_fa
            )
            description = care.get("description", "")

        except Exception as e:
            print("LLM Error:", e)
            care = {}
            description = ""

        # -------------------------------------------------------------
        # 5. Save NEW Record
        # -------------------------------------------------------------
        new_rec = await PlantHistory.create(
            user=user,
            image_path=saved_image_url,
            image_paths=[],
            plant_name=scientific_name,
            common_name_fa=common_name_fa,
            accuracy=accuracy,
            description=description,
            details=care if care else None,
        )

        return {
            "status": "success",
            "history_id": new_rec.id,
            "plant_name": scientific_name,
            "common_name_fa": common_name_fa,
            "accuracy": accuracy,
            "image_url": saved_image_url,
            "image_paths": [],
            **(care or {}),
        }
