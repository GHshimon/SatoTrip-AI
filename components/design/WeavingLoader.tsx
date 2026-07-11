/**
 * WeavingLoader — 「しおりが編まれる」生成待ちアニメーション
 *
 * AI プラン生成の待ち時間を世界観に転化する(DESIGN_PROPOSAL §6)。
 * 縦糸(経糸)の上に、趣味の和色の横糸(緯糸)が一本ずつ織られ、朱の杼が走る。
 *
 * 実装ノート(§7.5):
 * - rAF は必ず cleanup で cancel（StrictMode 二重マウント安全）
 * - prefers-reduced-motion では完成した織り上がりを静止表示
 * - タブ非表示時は rAF が自動停止するため追加対応不要
 */
import React, { useEffect, useRef } from 'react';
import { CATEGORY_TOKENS, HobbyCategory } from '../../src/design/tokens';

const WEFT_ORDER: HobbyCategory[] = [
  'touring', 'cafe', 'sauna', 'photo', 'nature', 'food', 'art', 'history',
];

interface WeavingLoaderProps {
  /** 表示サイズ(px) */
  size?: number;
  /** 一周の時間(ms)。生成の体感時間に合わせる */
  cycleMs?: number;
  theme?: 'light' | 'dark';
  className?: string;
}

export const WeavingLoader: React.FC<WeavingLoaderProps> = ({
  size = 280,
  cycleMs = 9000,
  theme = 'light',
  className,
}) => {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const S = size * dpr;
    canvas.width = S;
    canvas.height = S;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const warp = theme === 'dark' ? 'rgba(237,231,218,0.14)' : 'rgba(28,31,38,0.13)';
    const shuttle = theme === 'dark' ? '#E07A5F' : '#B5493A';
    const pad = S * 0.1;
    const area = S - pad * 2;
    const lines = 14;
    const gap = area / lines;

    const draw = (progress: number) => {
      ctx.clearRect(0, 0, S, S);
      // 経糸（固定の縦糸）
      ctx.lineWidth = dpr;
      ctx.strokeStyle = warp;
      for (let i = 0; i <= lines; i++) {
        const x = pad + i * gap;
        ctx.beginPath();
        ctx.moveTo(x, pad);
        ctx.lineTo(x, S - pad);
        ctx.stroke();
      }
      // 緯糸（趣味色。progress 分だけ織られる）
      const woven = progress * lines;
      const wovenFloor = Math.floor(woven);
      for (let j = 0; j <= wovenFloor && j <= lines; j++) {
        const y = pad + j * gap;
        const cat = CATEGORY_TOKENS[WEFT_ORDER[j % WEFT_ORDER.length]];
        ctx.strokeStyle = cat.chip;
        ctx.lineWidth = dpr * 2.2;
        ctx.globalAlpha = j === wovenFloor ? woven - wovenFloor : 1;
        ctx.beginPath();
        for (let x = pad; x <= S - pad; x += gap / 2) {
          const over = Math.floor((x - pad) / (gap / 2)) % 2 === j % 2;
          const yy = y + (over ? -1 : 1) * gap * 0.16;
          if (x === pad) ctx.moveTo(x, yy);
          else ctx.lineTo(x, yy);
        }
        ctx.stroke();
        ctx.globalAlpha = 1;
      }
      // 杼（シャトル）
      if (!reduced && wovenFloor <= lines) {
        const sy = pad + wovenFloor * gap;
        const sx = pad + (woven - wovenFloor) * area;
        ctx.fillStyle = shuttle;
        ctx.beginPath();
        ctx.ellipse(sx, sy, dpr * 7, dpr * 3, 0, 0, Math.PI * 2);
        ctx.fill();
      }
    };

    if (reduced) {
      draw(1); // 完成形を1回だけ静止描画
      return;
    }

    let raf = 0;
    let start: number | null = null;
    const frame = (ts: number) => {
      if (start === null) start = ts;
      draw(((ts - start) % cycleMs) / cycleMs);
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [size, cycleMs, theme]);

  return (
    <canvas
      ref={ref}
      className={className}
      style={{ width: size, height: size }}
      role="img"
      aria-label="プランを生成しています"
    />
  );
};

export default WeavingLoader;
