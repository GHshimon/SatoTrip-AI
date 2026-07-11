"""
ファイルストレージユーティリティ（ローカルディスク実装）
本番では S3 / Cloudinary 等に差し替え可能なように、保存処理をここに集約する。
"""
import os
import uuid
from app.config import settings

# 許可する画像MIMEタイプと拡張子
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def ensure_upload_dir() -> str:
    """アップロード用ディレクトリを作成して絶対パスを返す"""
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def save_avatar(content: bytes, content_type: str) -> str:
    """
    アバター画像を保存し、配信用の相対URL（/uploads/xxxx.png）を返す。
    呼び出し側でサイズ・MIME検証を済ませてから渡すこと。
    """
    ext = ALLOWED_IMAGE_TYPES.get(content_type, ".bin")
    filename = f"avatar_{uuid.uuid4().hex}{ext}"
    upload_dir = ensure_upload_dir()
    path = os.path.join(upload_dir, filename)
    with open(path, "wb") as f:
        f.write(content)
    # StaticFiles で /uploads にマウントして配信する
    return f"/uploads/{filename}"
