/**
 * TopoContour — 等高線背景（SVG + CSS）
 *
 * DESIGN_PROPOSAL §7.2 の確定事項に基づく初期実装。
 * WebGL ではなく「決定的に生成した等高線 SVG パス + CSS の超低速アニメ」で
 * 見た目の 9 割を再現する（省電力・端末互換・reduced-motion が安価）。
 * WebGL 版(fbm)は v2 で置換できるよう、親要素の背景レイヤーとして完結させる。
 */
import React, { useMemo } from 'react';

function seededRandom(seed: number): () => number {
  let s = seed >>> 0 || 1;
  return () => {
    s ^= s << 13;
    s ^= s >>> 17;
    s ^= s << 5;
    return (s >>> 0) / 4294967296;
  };
}

interface TopoContourProps {
  /** 決定性の種。同じ seed なら同じ地形 */
  seed?: number;
  /** 等高線の本数 */
  rings?: number;
  /** 線色。省略時は藍のトークン */
  stroke?: string;
  className?: string;
}

/** 半径 r を基準に、有機的に揺れた閉曲線の SVG パスを作る */
function contourPath(rnd: () => number, cx: number, cy: number, r: number, k: number): string {
  const pts: string[] = [];
  for (let a = 0; a <= Math.PI * 2 + 0.01; a += 0.16) {
    const wob = 0.1 * Math.sin(a * 2.3 + k * 0.7) + 0.07 * Math.sin(a * 5 + k) + 0.05 * rnd();
    const rr = r * (1 + wob);
    const x = +(cx + Math.cos(a) * rr).toFixed(1);
    const y = +(cy + Math.sin(a) * rr).toFixed(1);
    pts.push(`${pts.length ? 'L' : 'M'}${x} ${y}`);
  }
  return pts.join(' ') + ' Z';
}

export const TopoContour: React.FC<TopoContourProps> = ({
  seed = 3157,
  rings = 11,
  stroke = 'var(--st-ai)',
  className,
}) => {
  // パス生成は seed 依存の純粋計算。再レンダーで揺れないよう memo 化
  const paths = useMemo(() => {
    const rnd = seededRandom(seed);
    const out: string[] = [];
    // 2 つの「山」を重ねて地形らしさを出す
    for (let k = 0; k < rings; k++) {
      out.push(contourPath(rnd, 620, 380, 60 + k * 46, k));
    }
    for (let k = 0; k < Math.floor(rings * 0.6); k++) {
      out.push(contourPath(rnd, 180, 760, 40 + k * 38, k + 7));
    }
    return out;
  }, [seed, rings]);

  return (
    <div className={className} style={{ position: 'absolute', inset: 0, overflow: 'hidden' }} aria-hidden="true">
      <svg
        viewBox="0 0 1000 1000"
        preserveAspectRatio="xMidYMid slice"
        style={{ width: '100%', height: '100%', display: 'block' }}
      >
        <g className="st-topo-drift" fill="none" stroke={stroke} strokeWidth="1.1" opacity="0.2">
          {paths.map((d, i) => (
            <path key={i} d={d} className="st-topo-draw" style={{ animationDelay: `${i * 0.12}s` }} />
          ))}
        </g>
      </svg>
      {/* コンポーネント専用のスタイル。動きは「呼吸」1 種のみ・数十秒周期(§6) */}
      <style>{`
        .st-topo-drift {
          transform-origin: 50% 50%;
          animation: st-topo-breathe 60s ease-in-out infinite alternate;
        }
        .st-topo-draw {
          stroke-dasharray: 4000;
          stroke-dashoffset: 4000;
          animation: st-topo-draw 2.4s var(--st-ease, ease-out) forwards;
        }
        @keyframes st-topo-breathe {
          from { transform: scale(1) rotate(0deg); }
          to { transform: scale(1.06) rotate(1.2deg); }
        }
        @keyframes st-topo-draw {
          to { stroke-dashoffset: 0; }
        }
        @media (prefers-reduced-motion: reduce) {
          .st-topo-drift { animation: none; }
          .st-topo-draw { animation: none; stroke-dasharray: none; stroke-dashoffset: 0; }
        }
      `}</style>
    </div>
  );
};

export default TopoContour;
