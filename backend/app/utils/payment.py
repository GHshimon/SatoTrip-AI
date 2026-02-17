"""
決済機能（Stripe統合）
"""
import os
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

STRIPE_AVAILABLE = False
try:
    import stripe
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
    if STRIPE_SECRET_KEY:
        stripe.api_key = STRIPE_SECRET_KEY
        STRIPE_AVAILABLE = True
except ImportError:
    pass

from app.utils.subscription import PLANS


def create_checkout_session(plan_name: str, user_id: str, base_url: str, db) -> Optional[Dict[str, Any]]:
    """Stripe Checkout Sessionを作成"""
    if not STRIPE_AVAILABLE:
        return None
    
    if plan_name not in PLANS:
        return None
    
    plan = PLANS[plan_name]
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'jpy',
                    'product_data': {
                        'name': plan['name'],
                        'description': f"月{plan['monthly_plans'] if plan['monthly_plans'] != -1 else '無制限'}プラン生成"
                    },
                    'unit_amount': plan['price'] * 100,
                    'recurring': {'interval': 'month'},
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f'{base_url}?session_id={{CHECKOUT_SESSION_ID}}&user_id={user_id}',
            cancel_url=f'{base_url}?canceled=true',
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
        print(f"Stripeエラー: {e}")
        return None


def verify_payment(session_id: str, db) -> Optional[Dict[str, Any]]:
    """決済を検証"""
    if not STRIPE_AVAILABLE:
        return None
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status == 'paid':
            user_id = session.metadata.get('user_id')
            plan_name = session.metadata.get('plan_name')
            
            if user_id and plan_name:
                from app.utils.subscription import upgrade_plan
                upgrade_plan(db, user_id, plan_name, months=1)
                return {
                    'success': True,
                    'user_id': user_id,
                    'plan_name': plan_name,
                }
                return {
                    'success': True,
                    'user_id': user_id,
                    'plan_name': plan_name,
                }
        
        return {'success': False, 'status': session.payment_status}
    except Exception as e:
        print(f"決済検証エラー: {e}")
        return None

