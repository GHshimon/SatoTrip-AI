/**
 * ルート紋章（Route Crest）— 生成ロジック
 *
 * 「旅路のデータから、二つと無い紋章を決定的に生成する」ブランド資産の中核。
 * DESIGN_PROPOSAL.md §7.3 の確定事項に基づく設計:
 *
 * - 純粋関数: (CrestInput) → DrawCommand[]。Canvas/SVG/サーバ(OGP)どこでも描ける。
 * - 決定的: 同じ入力からは必ず同じ描画命令列が返る。Date.now()/Math.random() 禁止。
 * - バージョニング: CREST_ALGO_VERSION を上げない限り出力を変えてはならない。
 *   既に「刻印」された紋章の見た目を変えることは最大の運用事故と位置づける。
 *   （変更が必要になったら新バージョンを追加し、既存プランには旧バージョンを適用し続ける）
 *
 * 座標系: 0..1 の正方形正規化空間。中心 (0.5, 0.5)。レンダラ側で任意サイズに拡大する。
 * 色は hex ではなく「役割(ColorRole)」で持ち、レンダラがテーマに応じて解決する。
 */

export const CREST_ALGO_VERSION = 1;

/** 紋章の段階（§7.3） */
export type CrestState = 'brand' | 'empty' | 'draft' | 'complete';

/** レンダラがテーマで解決する色役割 */
export type ColorRole =
  | 'ring'        // 外周リング・コンパス目盛り（薄い墨）
  | 'contour'     // 内側の等高線の反響（さらに薄い墨）
  | 'accent'      // ルート線・方位星・起点（趣味色 or 朱）
  | 'paperFill';  // 経由点の抜き色（紙色）

export type DrawCommand =
  | {
      op: 'circle';
      x: number;
      y: number;
      r: number;
      stroke?: ColorRole;
      fill?: ColorRole;
      /** 線幅（正規化空間。レンダラ側で size を掛ける） */
      width?: number;
    }
  | {
      op: 'path';
      points: ReadonlyArray<readonly [number, number]>;
      close?: boolean;
      stroke?: ColorRole;
      fill?: ColorRole;
      width?: number;
      /** 破線パターン（正規化空間） */
      dash?: readonly number[];
    };

export interface CrestInput {
  state: CrestState;
  /**
   * 決定性の種。実プランでは seedFromString(plan.id) を使う。
   * brand 状態では BRAND_SEED を使う。
   */
  seed: number;
  /**
   * ルートの経由点（正規化 0..1 座標）。省略時は seed から導出する。
   * 実プランでは pointsFromCoords(スポット座標列) を渡す。
   */
  points?: ReadonlyArray<readonly [number, number]>;
}

/** 公式ブランド紋章の固定シード（変更禁止） */
export const BRAND_SEED = 20260710;

/* ------------------------------------------------------------ */
/* 決定的乱数・シード導出                                          */
/* ------------------------------------------------------------ */

/** xorshift32。同じ seed から必ず同じ列を返す。 */
function seededRandom(seed: number): () => number {
  let s = seed >>> 0 || 1;
  return () => {
    s ^= s << 13;
    s ^= s >>> 17;
    s ^= s << 5;
    return (s >>> 0) / 4294967296;
  };
}

/** 文字列(プランID等)から 32bit シードを導出（FNV-1a） */
export function seedFromString(input: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

/**
 * 実座標(緯度経度)列を紋章用の正規化座標へ。
 * バウンディングボックスを 0.24..0.76 に収め、縦横比は保つ。
 */
export function pointsFromCoords(
  coords: ReadonlyArray<{ lat: number; lng: number }>,
): Array<[number, number]> {
  if (coords.length === 0) return [];
  const lats = coords.map((c) => c.lat);
  const lngs = coords.map((c) => c.lng);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);
  const span = Math.max(maxLat - minLat, maxLng - minLng) || 1;
  const inner = 0.52; // 0.24..0.76
  return coords.map((c) => {
    const nx = (c.lng - minLng) / span;
    // 緯度は北が上になるよう反転
    const ny = 1 - (c.lat - minLat) / span;
    return [
      0.24 + nx * inner + (1 - (maxLng - minLng) / span) * inner * 0.5,
      0.24 + ny * inner - (1 - (maxLat - minLat) / span) * inner * 0.5,
    ];
  });
}

/* ------------------------------------------------------------ */
/* 生成本体                                                       */
/* ------------------------------------------------------------ */

const TICK_COUNT = 48;
const CONTOUR_COUNT = 5;
const CX = 0.5;
const CY = 0.5;

/**
 * 紋章の描画命令列を生成する（純粋・決定的）。
 * ここを変更する場合は CREST_ALGO_VERSION の項を必ず読むこと。
 */
export function buildCrestCommands(input: CrestInput): DrawCommand[] {
  const { state, seed } = input;
  const rnd = seededRandom(seed);
  const cmds: DrawCommand[] = [];

  // --- 外周ダブルリング（スタンプの縁）---
  cmds.push({ op: 'circle', x: CX, y: CY, r: 0.46, stroke: 'ring', width: 0.004 });
  cmds.push({ op: 'circle', x: CX, y: CY, r: 0.42, stroke: 'ring', width: 0.004 });

  // --- コンパス目盛り ---
  for (let i = 0; i < TICK_COUNT; i++) {
    const a = (i / TICK_COUNT) * Math.PI * 2;
    const rOuter = 0.42;
    const rInner = i % 4 === 0 ? 0.4 : 0.415;
    cmds.push({
      op: 'path',
      points: [
        [CX + Math.cos(a) * rOuter, CY + Math.sin(a) * rOuter],
        [CX + Math.cos(a) * rInner, CY + Math.sin(a) * rInner],
      ],
      stroke: 'ring',
      width: 0.004,
    });
  }

  // --- 内側の等高線の反響（empty 以外）---
  // ※ rnd の消費順は状態に依存させない。決定性のため必ず同じ回数呼ぶ。
  const contourWobbles: number[][] = [];
  for (let k = 0; k < CONTOUR_COUNT; k++) {
    const wobbles: number[] = [];
    const steps = Math.ceil((Math.PI * 2 + 0.1) / 0.18);
    for (let s = 0; s <= steps; s++) wobbles.push(rnd());
    contourWobbles.push(wobbles);
  }
  if (state !== 'empty') {
    for (let k = 0; k < CONTOUR_COUNT; k++) {
      const pts: Array<[number, number]> = [];
      let s = 0;
      for (let a = 0; a <= Math.PI * 2 + 0.1; a += 0.18) {
        const wob = 0.06 * Math.sin(a * 3 + k) + 0.05 * contourWobbles[k][s++];
        const rr = (0.15 + k * 0.05) * (1 + wob);
        pts.push([CX + Math.cos(a) * rr, CY + Math.sin(a) * rr]);
      }
      cmds.push({ op: 'path', points: pts, close: true, stroke: 'contour', width: 0.004 });
    }
  }

  // --- ルート経由点の決定（rnd 消費は状態に依存させない）---
  const derivedCount = 5 + Math.floor(rnd() * 3);
  const derived: Array<[number, number]> = [];
  for (let i = 0; i < derivedCount; i++) {
    const a = rnd() * Math.PI * 2;
    const rr = 0.11 + rnd() * 0.225;
    derived.push([CX + Math.cos(a) * rr, CY + Math.sin(a) * rr]);
  }
  const routePts: ReadonlyArray<readonly [number, number]> =
    input.points && input.points.length >= 2 ? input.points : derived;

  // --- ルート線＋経由点（brand / draft / complete のみ）---
  if (state !== 'empty') {
    cmds.push({
      op: 'path',
      points: routePts,
      stroke: 'accent',
      width: 0.008,
      ...(state === 'draft' ? { dash: [0.02, 0.016] as const } : {}),
    });
    routePts.forEach((p, i) => {
      cmds.push({
        op: 'circle',
        x: p[0],
        y: p[1],
        r: i === 0 ? 0.021 : 0.016,
        stroke: 'accent',
        width: 0.007,
        // draft は全点を抜き(未確定)、それ以外は起点のみ塗り潰し
        fill: state !== 'draft' && i === 0 ? 'accent' : 'paperFill',
      });
    });
  }

  // --- 中央の方位星（全状態共通のブランド署名）---
  const starPts: Array<[number, number]> = [];
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * Math.PI * 2 - Math.PI / 2;
    const rr = i % 2 ? 0.025 : 0.055;
    starPts.push([CX + Math.cos(a) * rr, CY + Math.sin(a) * rr]);
  }
  cmds.push({ op: 'path', points: starPts, close: true, fill: 'accent' });

  return cmds;
}

/* ------------------------------------------------------------ */
/* SVG レンダラ（サーバ/OGP/スナップショットでも使える）             */
/* ------------------------------------------------------------ */

export interface CrestColors {
  ring: string;
  contour: string;
  accent: string;
  paperFill: string;
}

export const CREST_COLORS: Record<'light' | 'dark', Omit<CrestColors, 'accent'>> = {
  light: { ring: 'rgba(28,31,38,0.22)', contour: 'rgba(28,31,38,0.09)', paperFill: '#FAF8F3' },
  dark: { ring: 'rgba(237,231,218,0.28)', contour: 'rgba(237,231,218,0.10)', paperFill: '#14171E' },
};

const fmt = (n: number, size: number) => +(n * size).toFixed(2);

/** 描画命令列を単体の SVG 文字列へ（プレビュー・スナップショット・将来の OGP 用） */
export function crestToSvg(
  cmds: readonly DrawCommand[],
  opts: { size: number; colors: CrestColors },
): string {
  const { size, colors } = opts;
  const resolve = (role?: ColorRole) => (role ? colors[role] : 'none');
  const parts: string[] = [];
  for (const c of cmds) {
    if (c.op === 'circle') {
      parts.push(
        `<circle cx="${fmt(c.x, size)}" cy="${fmt(c.y, size)}" r="${fmt(c.r, size)}" ` +
          `fill="${resolve(c.fill)}" stroke="${resolve(c.stroke)}" ` +
          `stroke-width="${fmt(c.width ?? 0, size)}"/>`,
      );
    } else {
      const d =
        c.points.map((p, i) => `${i ? 'L' : 'M'}${fmt(p[0], size)} ${fmt(p[1], size)}`).join(' ') +
        (c.close ? ' Z' : '');
      const dash = c.dash ? ` stroke-dasharray="${c.dash.map((v) => fmt(v, size)).join(' ')}"` : '';
      parts.push(
        `<path d="${d}" fill="${resolve(c.fill)}" stroke="${resolve(c.stroke)}" ` +
          `stroke-width="${fmt(c.width ?? 0, size)}" stroke-linejoin="round" stroke-linecap="round"${dash}/>`,
      );
    }
  }
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" ` +
    `viewBox="0 0 ${size} ${size}">${parts.join('')}</svg>`
  );
}
