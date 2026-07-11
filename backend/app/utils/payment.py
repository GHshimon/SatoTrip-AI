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
    あわせて Stripe の customer / subscription ID を保存し、
    以降の継続課金イベント（invoice.paid 等）との突合を可能にする。
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
    upgrade_plan(
        db, user_id, plan_name, months=1,
        stripe_customer_id=session.get("customer"),
        stripe_subscription_id=session.get("subscription"),
    )
    logger.info("Webhook: プランを昇格しました user=%s plan=%s", user_id, plan_name)
    return True


def _extract_invoice_subscription_id(invoice: Dict[str, Any]) -> Optional[str]:
    """
    invoice イベントから Stripe subscription ID を取り出す。
    APIバージョンにより位置が異なるため複数箇所を順に確認する。
    """
    # 旧来のトップレベル（大半のAPIバージョン）
    sub = invoice.get("subscription")
    if isinstance(sub, str) and sub:
        return sub
    if isinstance(sub, dict) and sub.get("id"):
        return sub["id"]
    # 2025年以降のAPIバージョン: parent.subscription_details.subscription
    parent = invoice.get("parent") or {}
    details = parent.get("subscription_details") or {}
    sub = details.get("subscription")
    if isinstance(sub, str) and sub:
        return sub
    # lines 側の parent からも辿れる場合がある
    for line in (invoice.get("lines") or {}).get("data", []):
        line_parent = line.get("parent") or {}
        item_details = line_parent.get("subscription_item_details") or {}
        sub = item_details.get("subscription")
        if isinstance(sub, str) and sub:
            return sub
    return None


def _extract_invoice_period_end(invoice: Dict[str, Any], subscription_id: Optional[str]) -> Optional[int]:
    """
    請求対象期間の終了時刻（unixtime）を取り出す。
    まず invoice の lines の period.end（最大値）を見て、
    取れなければ Stripe API で subscription の current_period_end を取得する。
    """
    period_ends = []
    for line in (invoice.get("lines") or {}).get("data", []):
        period = line.get("period") or {}
        end = period.get("end")
        if isinstance(end, (int, float)) and end > 0:
            period_ends.append(int(end))
    if period_ends:
        return max(period_ends)
    # フォールバック: subscription から current_period_end を取得
    if STRIPE_AVAILABLE and subscription_id:
        try:
            sub = stripe.Subscription.retrieve(subscription_id)
            end = sub.get("current_period_end")
            if isinstance(end, (int, float)) and end > 0:
                return int(end)
        except Exception as e:
            logger.warning("Stripe Subscription 取得エラー: %s", str(e))
    return None


def handle_invoice_paid(event, db) -> bool:
    """
    invoice.paid イベントを処理し、継続課金の入金で有効期限を延長する。
    これが無いと2ヶ月目以降「課金あり・無料プラン降格」が発生する。
    """
    from datetime import datetime, timedelta
    from app.utils.subscription import get_subscription_by_stripe_ids, extend_subscription

    invoice = event["data"]["object"]
    subscription_id = _extract_invoice_subscription_id(invoice)
    customer_id = invoice.get("customer")
    if isinstance(customer_id, dict):
        customer_id = customer_id.get("id")

    subscription = get_subscription_by_stripe_ids(
        db,
        stripe_subscription_id=subscription_id,
        stripe_customer_id=customer_id,
    )
    if not subscription:
        # 初回請求は checkout.session.completed 側で昇格・保存されるため、
        # ここで見つからないのは順序逆転か旧データ。スキップ（200を返す）。
        logger.warning(
            "Webhook: invoice.paid の対象ユーザーが見つかりません subscription=%s customer=%s",
            subscription_id, customer_id,
        )
        return False

    period_end_ts = _extract_invoice_period_end(invoice, subscription_id)
    if period_end_ts:
        expires_at = datetime.fromtimestamp(period_end_ts)
    else:
        # 期間が取れない場合の安全側フォールバック（1ヶ月延長）
        expires_at = datetime.now() + timedelta(days=30)

    # subscription_id が未保存だった場合はここで補完しておく
    if subscription_id and not subscription.stripe_subscription_id:
        subscription.stripe_subscription_id = subscription_id
    extend_subscription(db, subscription, expires_at)
    logger.info(
        "Webhook: 入金を確認し期限を延長しました user=%s plan=%s expires_at=%s",
        subscription.user_id, subscription.plan_name, expires_at.isoformat(),
    )
    return True


def handle_subscription_deleted(event, db) -> bool:
    """customer.subscription.deleted イベントを処理し、free に降格する。"""
    from app.utils.subscription import get_subscription_by_stripe_ids, downgrade_to_free

    stripe_sub = event["data"]["object"]
    subscription_id = stripe_sub.get("id")
    customer_id = stripe_sub.get("customer")
    if isinstance(customer_id, dict):
        customer_id = customer_id.get("id")

    subscription = get_subscription_by_stripe_ids(
        db,
        stripe_subscription_id=subscription_id,
        stripe_customer_id=customer_id,
    )
    if not subscription:
        logger.warning(
            "Webhook: subscription.deleted の対象ユーザーが見つかりません subscription=%s",
            subscription_id,
        )
        return False
    downgrade_to_free(db, subscription.user_id)
    logger.info("Webhook: 解約により free に降格しました user=%s", subscription.user_id)
    return True


def handle_payment_failed(event, db) -> bool:
    """invoice.payment_failed イベントを処理し、free に降格する。"""
    from app.utils.subscription import get_subscription_by_stripe_ids, downgrade_to_free

    invoice = event["data"]["object"]
    subscription_id = _extract_invoice_subscription_id(invoice)
    customer_id = invoice.get("customer")
    if isinstance(customer_id, dict):
        customer_id = customer_id.get("id")

    subscription = get_subscription_by_stripe_ids(
        db,
        stripe_subscription_id=subscription_id,
        stripe_customer_id=customer_id,
    )
    if not subscription:
        logger.warning(
            "Webhook: payment_failed の対象ユーザーが見つかりません subscription=%s customer=%s",
            subscription_id, customer_id,
        )
        return False
    downgrade_to_free(db, subscription.user_id)
    logger.info("Webhook: 支払失敗により free に降格しました user=%s", subscription.user_id)
    return True


def create_billing_portal_session(customer_id: str, return_url: str) -> Optional[str]:
    """Stripe カスタマーポータルのセッションを作成し、URLを返す。"""
    if not STRIPE_AVAILABLE:
        return None
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session.url
    except Exception as e:
        logger.error("Stripe カスタマーポータル作成エラー: %s", str(e))
        return None
