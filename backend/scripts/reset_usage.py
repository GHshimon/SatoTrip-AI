"""
使用量データをリセットするスクリプト
開発環境で月間の使用量をリセットする際に使用
"""
import sys
import os
import re
import logging
from datetime import datetime
from typing import Optional

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.utils.database import SessionLocal
from app.models.subscription import Usage

# ロギング設定（コンソール＋ファイル用の拡張性を保持）
logger = logging.getLogger(__name__)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_handler)
logger.setLevel(logging.INFO)

MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")


def _validate_month(month: str) -> bool:
    """month が YYYY-MM 形式か検証する。"""
    if not month or not MONTH_PATTERN.match(month):
        return False
    try:
        datetime.strptime(month + "-01", "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _normalize_month(month: Optional[str]) -> str:
    """None の場合は今月を YYYY-MM で返す。指定時は検証して返す。"""
    if month is None:
        now = datetime.now()
        return f"{now.year}-{now.month:02d}"
    if not _validate_month(month):
        raise ValueError(f"月は YYYY-MM 形式で指定してください: {month}")
    return month


def reset_monthly_usage(
    user_id: Optional[str] = None, month: Optional[str] = None
) -> None:
    """
    月間の使用量をリセット

    Args:
        user_id: リセットするユーザーID（Noneの場合は全ユーザー）
        month: リセットする月（YYYY-MM形式、Noneの場合は今月）

    Raises:
        ValueError: month が YYYY-MM 形式でない場合
    """
    db: Session = SessionLocal()

    try:
        month = _normalize_month(month)
        logger.info(
            "リセット対象: 月=%s, ユーザー=%s",
            month,
            user_id if user_id else "全ユーザー",
        )

        if user_id:
            usage = db.query(Usage).filter(
                Usage.user_id == user_id,
                Usage.month == month,
            ).first()

            if usage:
                old_value = usage.count
                usage.count = 0
                db.commit()
                logger.info(
                    "ユーザー '%s' の %s の使用量を %s -> 0 にリセットしました",
                    user_id,
                    month,
                    old_value,
                )
            else:
                logger.warning(
                    "ユーザー '%s' の %s の使用量データが見つかりません",
                    user_id,
                    month,
                )
        else:
            usages = db.query(Usage).filter(Usage.month == month).all()

            if usages:
                reset_count = 0
                for usage in usages:
                    old_value = usage.count
                    usage.count = 0
                    logger.info(
                        "ユーザー '%s' の %s の使用量を %s -> 0 にリセットしました",
                        usage.user_id,
                        month,
                        old_value,
                    )
                    reset_count += 1
                db.commit()
                logger.info("%d件の使用量データをリセットしました", reset_count)
            else:
                logger.warning("%s の使用量データが見つかりませんでした", month)

    except ValueError:
        raise
    except Exception as e:
        logger.exception("使用量リセット中にエラーが発生しました: %s", e)
        db.rollback()
        raise
    finally:
        db.close()


def show_usage() -> None:
    """現在の使用量を表示する。"""
    db: Session = SessionLocal()

    try:
        now = datetime.now()
        current_month = f"{now.year}-{now.month:02d}"

        logger.info("現在の使用量 (%s):", current_month)
        logger.info("-" * 50)

        usages = db.query(Usage).filter(Usage.month == current_month).all()

        if not usages:
            logger.info("使用量データがありません")
            return

        for usage in usages:
            logger.info("ユーザー: %s", usage.user_id)
            logger.info("  今月の使用量: %s回", usage.count)
            logger.info("")

    except Exception as e:
        logger.exception("使用量表示中にエラーが発生しました: %s", e)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="使用量データをリセット")
    parser.add_argument("--user", "-u", help="リセットするユーザーID（指定しない場合は全ユーザー）")
    parser.add_argument("--month", "-m", help="リセットする月（YYYY-MM形式、指定しない場合は今月）")
    parser.add_argument("--show", "-s", action="store_true", help="現在の使用量を表示")

    args = parser.parse_args()

    try:
        if args.show:
            show_usage()
        else:
            reset_monthly_usage(user_id=args.user, month=args.month)
    except ValueError as e:
        logger.error("%s", e)
        sys.exit(1)
    except Exception:
        sys.exit(1)
