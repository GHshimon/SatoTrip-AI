"""
メール送信ユーティリティ（標準ライブラリ smtplib）
SMTP_HOST が未設定の場合はメールを送らず、内容をログ出力する（開発用フォールバック）。
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.utils import formataddr
from app.config import settings

logger = logging.getLogger(__name__)


def is_smtp_configured() -> bool:
    return bool(settings.SMTP_HOST)


def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    メールを送信する。SMTP未設定なら送らずにログ出力し False を返す。
    送信成功時 True。例外は握りつぶさずログして False を返す。
    """
    if not is_smtp_configured():
        logger.warning(
            "[EMAIL-DEV] SMTP未設定のためメールを送信しません。宛先=%s 件名=%s\n本文:\n%s",
            to_email, subject, body
        )
        return False

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr(("SatoTrip", settings.SMTP_FROM))
    msg["To"] = to_email

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("メール送信成功: 宛先=%s 件名=%s", to_email, subject)
        return True
    except Exception as e:
        logger.error("メール送信失敗: %s", str(e))
        return False
