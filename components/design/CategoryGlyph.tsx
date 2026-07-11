/**
 * CategoryGlyph — 趣味カテゴリの線画グリフ（SVG）
 *
 * 「文字を読まなくても何のカードか分かる」ための視覚記号。
 * カード背景の透かし（大きく・薄く）にも、チップ内の小アイコンにも使う。
 * stroke は currentColor なので、色は親の color / 明示 color prop で制御する。
 */
import React from 'react';
import { HobbyCategory } from '../../src/design/tokens';

/** viewBox 48x48・stroke 線画。塗りは使わず線だけで構成する */
const GLYPH_PATHS: Record<HobbyCategory, React.ReactNode> = {
  // 峠道のルート（曲線＋起点・終点）
  touring: (
    <>
      <path d="M8 36 C 18 14, 28 44, 40 16" fill="none" />
      <circle cx="8" cy="36" r="2.6" fill="currentColor" stroke="none" />
      <circle cx="40" cy="16" r="2.6" fill="currentColor" stroke="none" />
    </>
  ),
  // コーヒー豆
  cafe: (
    <>
      <ellipse cx="24" cy="24" rx="12" ry="16" transform="rotate(28 24 24)" fill="none" />
      <path d="M18 12 C 28 20, 20 28, 30 36" fill="none" />
    </>
  ),
  // 湯気・水面の波
  sauna: (
    <>
      <path d="M6 18 q 6 -6 12 0 t 12 0 t 12 0" fill="none" />
      <path d="M6 27 q 6 -6 12 0 t 12 0 t 12 0" fill="none" opacity="0.75" />
      <path d="M6 36 q 6 -6 12 0 t 12 0 t 12 0" fill="none" opacity="0.5" />
    </>
  ),
  // カメラレンズ
  photo: (
    <>
      <circle cx="24" cy="24" r="14" fill="none" />
      <circle cx="24" cy="24" r="7" fill="none" />
      <circle cx="33" cy="15" r="1.8" fill="currentColor" stroke="none" />
    </>
  ),
  // 鳥居
  history: (
    <>
      <path d="M8 14 H 40" fill="none" />
      <path d="M10 21 H 38" fill="none" />
      <path d="M15 15 V 40 M 33 15 V 40" fill="none" />
    </>
  ),
  // 葉
  nature: (
    <>
      <path d="M24 42 C 38 32, 36 14, 24 6 C 12 14, 10 32, 24 42 Z" fill="none" />
      <path d="M24 10 V 40" fill="none" />
    </>
  ),
  // 椀と湯気
  food: (
    <>
      <path d="M10 26 a 14 14 0 0 0 28 0 Z" fill="none" />
      <path d="M8 26 H 40" fill="none" />
      <path d="M19 20 q 2 -3 0 -6 M 27 20 q 2 -3 0 -6" fill="none" opacity="0.7" />
    </>
  ),
  // 登り窯
  art: (
    <>
      <path d="M24 8 C 34 8, 38 22, 35 40 H 13 C 10 22, 14 8, 24 8 Z" fill="none" />
      <path d="M13 28 H 35" fill="none" />
    </>
  ),
};

interface CategoryGlyphProps {
  category: HobbyCategory;
  size?: number;
  color?: string;
  strokeWidth?: number;
  opacity?: number;
  className?: string;
  style?: React.CSSProperties;
}

export const CategoryGlyph: React.FC<CategoryGlyphProps> = ({
  category,
  size = 24,
  color,
  strokeWidth = 2.4,
  opacity,
  className,
  style,
}) => (
  <svg
    viewBox="0 0 48 48"
    width={size}
    height={size}
    aria-hidden="true"
    className={className}
    style={{ color, opacity, ...style }}
    stroke="currentColor"
    strokeWidth={strokeWidth}
    strokeLinecap="round"
    strokeLinejoin="round"
    fill="none"
  >
    {GLYPH_PATHS[category]}
  </svg>
);

export default CategoryGlyph;
