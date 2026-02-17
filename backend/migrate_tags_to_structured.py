"""
既存の文字列配列タグを構造化タグに変換するマイグレーションスクリプト
"""
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from app.utils.database import SessionLocal, init_db
from app.models.spot import Spot
from app.utils.tag_normalizer import normalize_tags, tags_to_dict_list, TagSource


def migrate_tags_to_structured(dry_run: bool = True):
    """
    既存の文字列配列タグを構造化タグに変換
    
    Args:
        dry_run: Trueの場合は実際の更新を行わず、変更内容を表示するのみ
    """
    db = SessionLocal()
    
    try:
        # タグが設定されている全スポットを取得
        spots = db.query(Spot).filter(Spot.tags.isnot(None)).all()
        
        print(f"対象スポット数: {len(spots)}")
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for spot in spots:
            try:
                current_tags = spot.tags
                
                # 既に構造化タグの場合はスキップ
                if isinstance(current_tags, list) and current_tags:
                    if isinstance(current_tags[0], dict) and "value" in current_tags[0]:
                        # 既に構造化タグ形式
                        skipped_count += 1
                        continue
                
                # 文字列配列を構造化タグに変換
                if isinstance(current_tags, list):
                    # 文字列リストの場合
                    structured_tags = normalize_tags(current_tags, source=TagSource.MIGRATION)
                    new_tags = tags_to_dict_list(structured_tags) if structured_tags else None
                elif isinstance(current_tags, str):
                    # 単一文字列の場合
                    structured_tags = normalize_tags([current_tags], source=TagSource.MIGRATION)
                    new_tags = tags_to_dict_list(structured_tags) if structured_tags else None
                else:
                    # その他の形式はスキップ
                    print(f"  警告: スポット {spot.id} ({spot.name}) のタグ形式が不明です: {type(current_tags)}")
                    skipped_count += 1
                    continue
                
                if not dry_run:
                    # 実際に更新
                    spot.tags = new_tags
                    db.commit()
                    updated_count += 1
                    print(f"  ✓ 更新: {spot.name} ({len(new_tags) if new_tags else 0}個のタグ)")
                else:
                    # ドライランの場合は表示のみ
                    print(f"  [DRY RUN] 更新予定: {spot.name}")
                    print(f"    現在: {current_tags}")
                    print(f"    更新後: {new_tags}")
                    updated_count += 1
                    
            except Exception as e:
                error_count += 1
                print(f"  ✗ エラー: スポット {spot.id} ({spot.name}) の更新に失敗: {str(e)}")
        
        print("\n=== マイグレーション結果 ===")
        print(f"更新: {updated_count}件")
        print(f"スキップ: {skipped_count}件")
        print(f"エラー: {error_count}件")
        
        if dry_run:
            print("\n※ これはドライランです。実際の更新を行うには dry_run=False を指定してください。")
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="既存の文字列配列タグを構造化タグに変換")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に更新を実行（指定しない場合はドライラン）"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("タグ構造化マイグレーション")
    print("=" * 60)
    
    if not args.execute:
        print("\n⚠️  ドライランモードで実行します（実際の更新は行いません）")
        print("   実際に更新するには --execute フラグを指定してください\n")
    
    migrate_tags_to_structured(dry_run=not args.execute)

