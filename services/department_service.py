from core.logger import db_logger
from models.department import Department
from tortoise.exceptions import DoesNotExist


class DepartmentService:

    async def create_department(self, name: str):
        """ایجاد دپارتمان جدید"""
        db_logger.logger.info(f"Creating department: {name}")

        dept = await Department.create(name=name, is_active=True)

        db_logger.log_create("Department", {
            "id": dept.id,
            "name": name
        })

        return self.serialize(dept)

    async def get_all_departments(self, active_only: bool = True):
        """دریافت لیست دپارتمان‌ها"""
        query = Department.all()

        if active_only:
            query = query.filter(is_active=True)

        depts = await query.order_by("id")

        db_logger.logger.debug(f"Retrieved {len(depts)} departments")

        return [self.serialize(d) for d in depts]

    async def get_department(self, dept_id: int):
        """دریافت یک دپارتمان"""
        try:
            dept = await Department.get(id=dept_id)
            return self.serialize(dept)
        except DoesNotExist:
            db_logger.logger.warning(f"Department {dept_id} not found")
            return None

    async def update_department(self, dept_id: int, name: str = None, is_active: bool = None):
        """به‌روزرسانی دپارتمان"""
        dept = await Department.get(id=dept_id)

        changes = {}
        if name is not None:
            dept.name = name
            changes["name"] = name

        if is_active is not None:
            dept.is_active = is_active
            changes["is_active"] = is_active

        await dept.save()

        db_logger.log_update("Department", dept_id, changes)

        return self.serialize(dept)

    async def delete_department(self, dept_id: int):
        """حذف دپارتمان (اگر چتی نداشته باشه)"""
        dept = await Department.get(id=dept_id)

        # ✅ چک کردن اینکه آیا چتی داره یا نه
        has_conversations = await dept.conversations.all().count() > 0

        if has_conversations:
            db_logger.logger.warning(
                f"Cannot delete department {dept_id}: has active conversations"
            )
            return False

        await dept.delete()
        db_logger.log_delete("Department", dept_id)

        return True

    def serialize(self, dept: Department):
        """تبدیل به dict"""
        return {
            "id": dept.id,
            "name": dept.name,
            "is_active": dept.is_active,
            "created_at": dept.created_at.isoformat()
        }
