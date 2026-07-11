"""
決済API（Stripe）
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.utils.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.config import settings
from app.utils import payment as payment_util
from app.utils.subscription import PLANS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["payments"])


class CheckoutRequest(BaseModel):
    plan_name: str


@router.get("/config")
async def get_payment_config():
    """フロント向けの公開設定（公開可能キーと有効状態）"""
    return {
        "configured": payment_util.is_configured(),
        "publishable_key": settings.STRIPE_PUBLISHABLE_KEY or None,
    }


@router.post("/checkout")
async def create_checkout(
    payload: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stripe Checkout セッションを作成し、決済URLを返す"""
    if not payment_util.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="決済機能は現在利用できません（サーバー未設定）"
        )
    if payload.plan_name not in PLANS or payload.plan_name == "free":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="指定のプランは購入できません"
        )
    base_url = settings.FRONTEND_URL.rstrip("/") + "/settings"
    result = payment_util.create_checkout_session(
        payload.plan_name, current_user.id, base_url, db
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="決済セッションの作成に失敗しました"
        )
    return result


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Stripe Webhook 受信口。署名を検証し、checkout.session.completed で昇格する。
    昇格はこの検証済みイベントでのみ行い、クライアント由来のパラメータは信頼しない。
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event = payment_util.construct_webhook_event(payload, sig_header)
    except ValueError as e:
        # 署名不正・未設定など。イベントは処理しない。
        logger.warning("Stripe Webhook 検証失敗: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook署名の検証に失敗しました"
        )
    except Exception as e:
        logger.warning("Stripe Webhook 検証失敗（署名不一致）: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook署名の検証に失敗しました"
        )

    if event.get("type") == "checkout.session.completed":
        payment_util.handle_checkout_completed(event, db)

    return {"received": True}
