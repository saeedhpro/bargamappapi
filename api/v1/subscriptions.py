from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from api.deps import get_current_user
from models.user import User
from services.subscription import SubscriptionService
from schemas.subscription import SubscriptionPlanOut, PurchaseResult

router = APIRouter(prefix="/api/v1/subscriptions", tags=["Subscriptions"])


@router.get("/plans", response_model=List[SubscriptionPlanOut])
async def get_plans(
        current_user: User = Depends(get_current_user)
):
    """
    لیست اشتراک‌های قابل خرید.
    اگر کاربر اشتراک فعال داشته باشد، آرایه خالی برمی‌گردد.
    """
    plans = await SubscriptionService.get_sellable_plans(current_user.id)
    return plans


@router.post("/purchase/{plan_id}", response_model=PurchaseResult)
async def purchase_plan(
        plan_id: int,
        current_user: User = Depends(get_current_user)
):
    """
    خرید (فعال‌سازی) یک اشتراک خاص.
    در سناریوی واقعی اینجا باید به درگاه پرداخت وصل شود.
    """
    try:
        # نکته: قبل از خرید دوباره چک کنید که کاربر اشتراک نداشته باشد
        sellable_plans = await SubscriptionService.get_sellable_plans(current_user.id)
        if not sellable_plans:
            # یعنی کاربر مجاز به دیدن لیست نبوده (پس مجاز به خرید هم نیست)
            # مگر اینکه بخواهید اجازه دهید اشتراک را تمدید کند (که لاجیکش فرق دارد)
            raise HTTPException(
                status_code=400,
                detail="شما در حال حاضر اشتراک فعال دارید."
            )

        sub = await SubscriptionService.activate_subscription(current_user, plan_id)

        return PurchaseResult(
            success=True,
            message="اشتراک با موفقیت فعال شد.",
            expires_at=str(sub.end_date)
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(str(e))
        raise HTTPException(status_code=500, detail=f"Internal Error: {str(e)}")
