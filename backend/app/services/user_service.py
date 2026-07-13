"""
ユーザーサービス
"""
import logging
import os

from sqlalchemy.orm import Session
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.models.spot_favorite import SpotFavorite
from app.models.subscription import Subscription, Usage
from app.models.user_preferences import UserPreferences
from app.models.api_key import ApiKey
from app.models.plan import Plan
from app.models.plan_folder import PlanFolder
from app.utils import payment as payment_util
from app.config import settings
from typing import Optional
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def get_user(db: Session, user_id: str) -> Optional[User]:
    """ユーザーを取得"""
    return db.query(User).filter(User.id == user_id).first()


def update_user(db: Session, user_id: str, user_data: dict) -> User:
    """ユーザーを更新"""
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません"
        )
    
    # 更新
    if "name" in user_data and user_data["name"] is not None:
        user.name = user_data["name"]
    if "email" in user_data and user_data["email"] is not None:
        # メールアドレスの重複チェック
        existing_user = db.query(User).filter(
            User.email == user_data["email"],
            User.id != user_id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="このメールアドレスは既に使用されています"
            )
        user.email = user_data["email"]
    if "avatar" in user_data:
        user.avatar = user_data["avatar"]
    
    db.commit()
    db.refresh(user)
    return user


def _delete_avatar_file(avatar: Optional[str]) -> None:
    """アバターの実ファイルを削除する（ベストエフォート、失敗は無視）"""
    # save_avatar が返す "/uploads/xxxx.ext" 形式のみ対象（外部URL等は触らない）
    if not avatar or not avatar.startswith("/uploads/"):
        return
    try:
        filename = os.path.basename(avatar)
        path = os.path.join(os.path.abspath(settings.UPLOAD_DIR), filename)
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        # ファイル削除の失敗で退会処理を止めない
        pass


def delete_user_account(db: Session, user: User) -> None:
    """
    退会（アカウント削除）。ユーザー本体と関連データを全て削除する。
    DBレベルのカスケードは未設定のため、依存する順にここで明示削除する。
    失敗時はロールバックして例外を再送出する（呼び出し側で500に変換）。
    """
    # Stripe のサブスクリプションを即時解約（ベストエフォート。失敗しても退会は続行）
    subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if subscription and subscription.stripe_subscription_id and payment_util.is_configured():
        if not payment_util.cancel_stripe_subscription(subscription.stripe_subscription_id):
            logger.warning(
                "退会時のStripe解約に失敗しました user=%s subscription=%s",
                user.id, subscription.stripe_subscription_id,
            )

    try:
        # 関連データを依存の浅い順に削除する
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete(
            synchronize_session=False
        )
        db.query(SpotFavorite).filter(SpotFavorite.user_id == user.id).delete(
            synchronize_session=False
        )
        db.query(Usage).filter(Usage.user_id == user.id).delete(synchronize_session=False)
        # Subscription は user_id ユニークで最大1件。上で取得済みのオブジェクトを
        # ORM で削除する（bulk delete だとセッション上の残骸が最終flushで不整合になる）
        if subscription:
            db.delete(subscription)
        db.query(UserPreferences).filter(UserPreferences.user_id == user.id).delete(
            synchronize_session=False
        )
        # ApiKey は api_key_usage への ORM カスケード（all, delete-orphan）を効かせるため
        # bulk delete ではなく必ず1件ずつ db.delete() する
        for api_key in db.query(ApiKey).filter(ApiKey.user_id == user.id).all():
            db.delete(api_key)
        # Plan はフォルダより先に削除（folder_id の FK 参照があるため）
        db.query(Plan).filter(Plan.user_id == user.id).delete(synchronize_session=False)
        # PlanFolder は parent_id の自己参照FKがあるため、bulk delete ではなく
        # 1件ずつ db.delete() する（ORM が子の parent_id を NULL 化してから削除する）
        for folder in db.query(PlanFolder).filter(PlanFolder.user_id == user.id).all():
            db.delete(folder)

        # アバターの実ファイルを削除（ベストエフォート）
        _delete_avatar_file(user.avatar)

        # 最後にユーザー本体を削除
        db.delete(user)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("退会処理に失敗しました user=%s", user.id)
        raise

