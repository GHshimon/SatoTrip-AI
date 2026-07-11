"""
決済API（Stripe）
"""
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.utils.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.subscription import Subscription
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
    # Stripe SDK は同期I/Oのためスレッドへ逃がす（イベントループを塞がない）
    result = await asyncio.to_thread(
        payment_util.create_checkout_session,
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

    event_type = event.get("type")
    if event_type == "checkout.session.completed":
        # 初回決済: プラン昇格＋Stripe customer/subscription ID を保存
        await asyncio.to_thread(payment_util.handle_checkout_completed, event, db)
    elif event_type == "invoice.paid":
        # 継続課金: 有効期限を period_end まで延長
        await asyncio.to_thread(payment_util.handle_invoice_paid, event, db)
    elif event_type == "customer.subscription.deleted":
        # 解約完了: free に降格
        await asyncio.to_thread(payment_util.handle_subscription_deleted, event, db)
    elif event_type == "invoice.payment_failed":
        # 支払失敗: free に降格
        await asyncio.to_thread(payment_util.handle_payment_failed, event, db)
    # 上記以外のイベントは何もせず 200 を返す（Stripe の再送を防ぐ）

    return {"received": True}


@router.post("/portal")
async def create_billing_portal(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Stripe カスタマーポータルのセッションを作成し、URLを返す。
    解約・支払方法変更・請求履歴の確認はポータル側で行う。
    """
    if not payment_util.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="決済機能は現在利用できません（サーバー未設定）"
        )
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    if not subscription or not subscription.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="サブスクリプションが見つかりません"
        )
    return_url = settings.FRONTEND_URL.rstrip("/") + "/#/settings"
    url = await asyncio.to_thread(
        payment_util.create_billing_portal_session,
        subscription.stripe_customer_id,
        return_url,
    )
    if not url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="カスタマーポータルの作成に失敗しました"
        )
    return {"url": url}
