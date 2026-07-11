"""
決済機能（Stripe統合）
"""
import logging
from typing import Optional, Dict, Any

from app.config import settings
from app.utils.subscription import PLANS

logger = logging.getLogger(__name__)

STRIPE_AVAILABLE = False
stripe = None
try:
    import stripe as _stripe
    stripe = _stripe
    if settings.STRIPE_SECRET_KEY:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        STRIPE_AVAILABLE = True
except ImportError:
    logger.warning("stripe パッケージが見つかりません。決済機能は無効です。")

# Stripe のゼロ十進通貨（最小単位が通貨単位そのもの。例: JPY は「円」が最小単位）
# これらの通貨では unit_amount に金額をそのまま渡す（×100してはいけない）。
ZERO_DECIMAL_CURRENCIES = {
    "jpy", "krw", "vnd", "clp", "bif", "djf", "gnf",
    "kmf", "mga", "pyg", "rwf", "ugx", "vuv", "xaf", "xof", "xpf",
}


def is_configured() -> bool:
    return STRIPE_AVAILABLE


def stripe_unit_amount(price: int, currency: str = "jpy") -> int:
    """
    Stripe の unit_amount を算出する。
    ゼロ十進通貨（JPY等）はそのまま、それ以外は最小単位（セント等）に変換するため×100。
    """
    if currency.lower() in ZERO_DECIMAL_CURRENCIES:
        return price
    return price * 100


def create_checkout_session(plan_name: str, user_id: str, base_url: str, db) -> Optional[Dict[str, Any]]:
    """Stripe Checkout Sessionを作成"""
    if not STRIPE_AVAILABLE:
        return None
    if plan_name not in PLANS:
        return None

    plan = PLANS[plan_name]
    currency = "jpy"

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': currency,
                    'product_data': {
                        'name': plan['name'],
                        'description': f"月{plan['monthly_plans'] if plan['monthly_plans'] != -1 else '無制限'}プラン生成"
                    },
                    # JPY はゼロ十進通貨のため金額をそのまま渡す（従来の ×100 は 100倍請求のバグ）
                    'unit_amount': stripe_unit_amount(plan['price'], currency),
                    'recurring': {'interval': 'month'},
                },
                'quantity': 1,
            }],
            mode='subscription',
            # 昇格は Webhook（署名検証済み）でのみ行う。success_url のパラメータは信頼しない。
            success_url=f'{base_url}?checkout=success&session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{base_url}?checkout=canceled',
            metadata={
                'user_id': user_id,
                'plan_name': plan_name,
            },
        )
        return {
            'session_id': session.id,
            'url': session.url,
        }
    except Exception as e:
        logger.error("Stripe Checkout 作成エラー: %s", str(e))
        return None


def construct_webhook_event(payload: bytes, sig_header: str):
    """
    Webhook の署名を検証してイベントを構築する。
    署名不正・シークレット未設定時は例外を送出する。
    """
    if not STRIPE_AVAILABLE:
        raise ValueError("Stripe が設定されていません")
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise ValueError("STRIPE_WEBHOOK_SECRET が未設定です")
    # 署名検証（改ざん・なりすましを防ぐ）。失敗時は例外を送出する。
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )


def handle_checkout_completed(event, db) -> bool:
    """
    checkout.session.completed イベントを処理してプランを昇格する。
    metadata（サーバー側で設定した値）のみを信頼する。
    """
    session = event["data"]["object"]
    if session.get("payment_status") != "paid":
        return False
    metadata = session.get("metadata") or {}
    user_id = metadata.get("user_id")
    plan_name = metadata.get("plan_name")
    if not user_id or plan_name not in PLANS:
        logger.warning("Webhook: 不正な metadata（昇格スキップ）")
        return False
    from app.utils.subscription import upgrade_plan
    upgrade_plan(db, user_id, plan_name, months=1)
    logger.info("Webhook: プランを昇格しました user=%s plan=%s", user_id, plan_name)
    return True
