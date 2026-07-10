/**
 * RouteCrest — ルート紋章の表示コンポーネント
 *
 * 生成は src/design/crest.ts の純粋関数に完全委譲し、ここは描画のみを担う。
 * - StrictMode の二重マウントに安全（描画は冪等な1回描き。rAF ループを持たない）
 * - 一覧に多数並べても負荷が増えない静的描画（DESIGN_PROPOSAL.md §7.5）
 */
import React, { useEffect, useRef } from 'react';
import {
  buildCrestCommands,
  CREST_COLORS,
  CrestInput,
  DrawCommand,
  ColorRole,
} from '../src/design/crest';
import { BASE_TOKENS, ThemeName } from '../src/design/tokens';

export interface RouteCrestProps extends CrestInput {
  /** 表示サイズ(px)。描画は devicePixelRatio を掛けて鮮明に行う */
  size?: number;
  /** 紋章のアクセント色。省略時は朱 */
  accent?: string;
  theme?: ThemeName;
  className?: string;
  'aria-label'?: string;
}

function drawToCanvas(
  canvas: HTMLCanvasElement,
  cmds: readonly DrawCommand[],
  size: number,
  colors: Record<ColorRole, string>,
): void {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const px = size * dpr;
  canvas.width = px;
  canvas.height = px;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  ctx.clearRect(0, 0, px, px);
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  for (const c of cmds) {
    ctx.beginPath();
    if (c.op === 'circle') {
      ctx.arc(c.x * px, c.y * px, c.r * px, 0, Math.PI * 2);
    } else {
      c.points.forEach((p, i) =>
        i ? ctx.lineTo(p[0] * px, p[1] * px) : ctx.moveTo(p[0] * px, p[1] * px),
      );
      if (c.close) ctx.closePath();
    }
    if (c.fill) {
      ctx.fillStyle = colors[c.fill];
      ctx.fill();
    }
    if (c.stroke) {
      ctx.strokeStyle = colors[c.stroke];
      ctx.lineWidth = Math.max(1, (c.width ?? 0.004) * px);
      ctx.setLineDash(c.op === 'path' && c.dash ? c.dash.map((v) => v * px) : []);
      ctx.stroke();
    }
  }
}

export const RouteCrest: React.FC<RouteCrestProps> = ({
  state,
  seed,
  points,
  size = 180,
  accent,
  theme = 'light',
  className,
  'aria-label': ariaLabel,
}) => {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const cmds = buildCrestCommands({ state, seed, points });
    const base = CREST_COLORS[theme];
    const colors: Record<ColorRole, string> = {
      ...base,
      accent: accent ?? BASE_TOKENS[theme].shu,
    };
    drawToCanvas(canvas, cmds, size, colors);
    // 静的描画のためクリーンアップ不要（タイマー・rAF・購読を持たない）
  }, [state, seed, points, size, accent, theme]);

  return (
    <canvas
      ref={ref}
      className={className}
      style={{ width: size, height: size }}
      role="img"
      aria-label={ariaLabel ?? 'ルート紋章'}
    />
  );
};

export default RouteCrest;
