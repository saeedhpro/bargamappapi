from datetime import datetime, timedelta
import jdatetime
from fastapi import HTTPException, status
from tortoise.functions import Count

# فرض بر این است که User مدل شماست. برای تایپ هینتینگ استفاده می‌شود
# اگر ایمپورت User باعث سیکل شد، می‌توانید تایپ آن را Any بگذارید یا فقط id بگیرید
from models.user import User
from models.subscription import SubscriptionPlan, UserSubscription, UsageLog, ToolType
from schemas.user import ActiveSubscriptionInfo


class SubscriptionService:

    @staticmethod
    async def activate_subscription(user: User, plan_id: int) -> UserSubscription:
        """
        فعال‌سازی یک اشتراک جدید برای کاربر.
        این متد مقادیر لیمیت را از پلن کپی می‌کند (Snapshot).
        """
        # ۱. پیدا کردن پلن
        plan = await SubscriptionPlan.get_or_none(id=plan_id)
        if not plan:
            raise ValueError("پلن مورد نظر یافت نشد.")

        # ۲. محاسبه تاریخ انقضا
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=plan.duration_days)

        # ۳. غیرفعال کردن اشتراک‌های پولی قبلی (اصلاح شده برای رفع خطای SQL)
        # گام اول: پیدا کردن ID اشتراک‌های پولی فعال (SELECT - Join مجاز است)
        old_premium_sub_ids = await UserSubscription.filter(
            user=user,
            is_active=True,
            plan__is_default=False
        ).values_list('id', flat=True)

        # گام دوم: غیرفعال کردن بر اساس ID (UPDATE ساده - بدون Join)
        if old_premium_sub_ids:
            await UserSubscription.filter(id__in=old_premium_sub_ids).update(is_active=False)

        # ۴. ایجاد اشتراک جدید با Snapshot لیمیت‌ها
        new_subscription = await UserSubscription.create(
            user=user,
            plan=plan,
            # نکته مهم: کپی کردن مقادیر در لحظه خرید (Frozen)
            frozen_daily_plant_id_limit=plan.daily_plant_id_limit,
            frozen_daily_disease_id_limit=plan.daily_disease_id_limit,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )

        return new_subscription

    @staticmethod
    async def check_and_record_usage(user_id: int, tool_type: ToolType):
        """
        بررسی می‌کند آیا کاربر مجاز به استفاده از ابزار هست یا خیر.
        """
        now = datetime.utcnow()

        # ۱. پیدا کردن اشتراک فعال (پولی یا رایگان)
        active_sub = await UserSubscription.filter(
            user_id=user_id,
            is_active=True,
            plan__is_default=False,
            end_date__gt=now
        ).first()

        if not active_sub:
            active_sub = await UserSubscription.filter(
                user_id=user_id,
                is_active=True,
                plan__is_default=True
            ).first()

        if not active_sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="هیچ اشتراک فعالی یافت نشد."
            )

        # ۲. تعیین لیمیت
        limit = 0
        if tool_type == ToolType.PLANT_ID:
            limit = active_sub.frozen_daily_plant_id_limit
        elif tool_type == ToolType.DISEASE_ID:
            limit = active_sub.frozen_daily_disease_id_limit

        # ۳. محاسبه بازه زمانی امروز (شمسی)
        now_jalali = jdatetime.datetime.now()
        start_of_day_jalali = now_jalali.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_day_gregorian = start_of_day_jalali.togregorian()

        # ۴. شمارش استفاده‌های امروز
        usage_count = await UsageLog.filter(
            user_id=user_id,
            tool_type=tool_type,
            created_at__gte=start_of_day_gregorian
        ).count()

        # ۵. بررسی لیمیت
        if usage_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="محدودیت استفاده روزانه شما تمام شده است."
            )

        # ۶. ثبت استفاده
        await UsageLog.create(
            user_id=user_id, # استفاده از ID امن‌تر است اگر آبجکت یوزر در دسترس نباشد
            subscription=active_sub,
            tool_type=tool_type,
            created_at=now
        )

        return True

    @staticmethod
    async def assign_default_plan(user_id: int) -> UserSubscription:
        """اختصاص پلن رایگان به کاربر."""
        default_plan = await SubscriptionPlan.get_or_none(is_default=True)

        if not default_plan:
            default_plan = await SubscriptionPlan.create(
                title="پلن رایگان پایه",
                description="سیستمی",
                price=0,
                duration_days=3650,
                daily_plant_id_limit=1,
                daily_disease_id_limit=1,
                is_default=True,
                is_active=True
            )

        existing_sub = await UserSubscription.get_or_none(
            user_id=user_id,
            plan=default_plan,
            is_active=True
        )
        if existing_sub:
            return existing_sub

        new_sub = await UserSubscription.create(
            user_id=user_id,
            plan=default_plan,
            frozen_daily_plant_id_limit=default_plan.daily_plant_id_limit,
            frozen_daily_disease_id_limit=default_plan.daily_disease_id_limit,
            start_date=datetime.utcnow(),
            end_date=None,
            is_active=True
        )
        return new_sub

    @staticmethod
    async def get_user_active_subscription_info(user_id: int) -> ActiveSubscriptionInfo:
        """دریافت اطلاعات اشتراک فعال."""
        now = datetime.utcnow()

        premium_sub = await UserSubscription.filter(
            user_id=user_id,
            is_active=True,
            plan__is_default=False,
            end_date__gt=now
        ).prefetch_related('plan').first()

        if premium_sub:
            return ActiveSubscriptionInfo(
                plan_title=premium_sub.plan.title,
                is_premium=True,
                expires_at=premium_sub.end_date,
                daily_plant_limit=premium_sub.frozen_daily_plant_id_limit,
                daily_disease_limit=premium_sub.frozen_daily_disease_id_limit
            )

        free_sub = await UserSubscription.filter(
            user_id=user_id,
            is_active=True,
            plan__is_default=True
        ).prefetch_related('plan').first()

        if free_sub:
            return ActiveSubscriptionInfo(
                plan_title=free_sub.plan.title,
                is_premium=False,
                expires_at=None,
                daily_plant_limit=free_sub.frozen_daily_plant_id_limit,
                daily_disease_limit=free_sub.frozen_daily_disease_id_limit
            )

        return ActiveSubscriptionInfo(
            plan_title="بدون اشتراک",
            is_premium=False,
            daily_plant_limit=0,
            daily_disease_limit=0
        )

    @staticmethod
    async def get_sellable_plans(user_id: int):
        """لیست پلن‌های قابل فروش."""
        now = datetime.utcnow()
        has_active_premium = await UserSubscription.filter(
            user_id=user_id,
            is_active=True,
            plan__is_default=False,
            end_date__gt=now
        ).exists()

        if has_active_premium:
            return []

        return await SubscriptionPlan.filter(is_active=True, is_default=False).all()
