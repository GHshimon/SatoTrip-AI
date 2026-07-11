/**
 * ルート紋章の後方互換テスト（DESIGN_PROPOSAL.md §7.3）
 *
 * ここのスナップショットが割れた = 「発行済みの紋章の見た目が変わった」。
 * 意図的な変更なら CREST_ALGO_VERSION を上げ、旧バージョンの出力を維持する
 * 経路を用意すること。安易にスナップショットを更新してはならない。
 */
import { describe, expect, it } from 'vitest';
import {
  BRAND_SEED,
  buildCrestCommands,
  CREST_ALGO_VERSION,
  crestToSvg,
  CREST_COLORS,
  pointsFromCoords,
  seedFromString,
} from './crest';

describe('crest determinism', () => {
  it('同じ入力からは常に同じ命令列が返る', () => {
    const a = buildCrestCommands({ state: 'complete', seed: 7731 });
    const b = buildCrestCommands({ state: 'complete', seed: 7731 });
    expect(a).toEqual(b);
  });

  it('シードが違えば異なる紋章になる', () => {
    const a = JSON.stringify(buildCrestCommands({ state: 'complete', seed: 7731 }));
    const b = JSON.stringify(buildCrestCommands({ state: 'complete', seed: 4412 }));
    expect(a).not.toBe(b);
  });

  it('状態が変わってもルート形状(rnd消費)は変わらない', () => {
    // draft と complete で同じ seed → 経由点座標は一致しなければならない
    const draft = buildCrestCommands({ state: 'draft', seed: 9987 });
    const complete = buildCrestCommands({ state: 'complete', seed: 9987 });
    const circles = (cmds: ReturnType<typeof buildCrestCommands>) =>
      cmds.filter((c) => c.op === 'circle' && c.r < 0.1).map((c) => (c.op === 'circle' ? [c.x, c.y] : null));
    expect(circles(draft)).toEqual(circles(complete));
  });

  it('seedFromString は安定している', () => {
    expect(seedFromString('plan-123')).toBe(seedFromString('plan-123'));
    expect(seedFromString('plan-123')).not.toBe(seedFromString('plan-124'));
  });

  it('pointsFromCoords は 0.24..0.76 に正規化する', () => {
    const pts = pointsFromCoords([
      { lat: 35.0, lng: 137.0 },
      { lat: 35.2, lng: 137.3 },
      { lat: 34.9, lng: 137.15 },
    ]);
    for (const [x, y] of pts) {
      expect(x).toBeGreaterThanOrEqual(0.2);
      expect(x).toBeLessThanOrEqual(0.8);
      expect(y).toBeGreaterThanOrEqual(0.2);
      expect(y).toBeLessThanOrEqual(0.8);
    }
  });
});

describe('crest backward compatibility (v1)', () => {
  it('アルゴリズムバージョンは 1', () => {
    expect(CREST_ALGO_VERSION).toBe(1);
  });

  // 固定 fixture のスナップショット。割れたら上のヘッダコメントを読むこと。
  const FIXTURES = [
    { name: 'brand', input: { state: 'brand', seed: BRAND_SEED } as const },
    { name: 'empty', input: { state: 'empty', seed: 424242 } as const },
    { name: 'draft', input: { state: 'draft', seed: 7731 } as const },
    { name: 'complete', input: { state: 'complete', seed: 7731 } as const },
    {
      name: 'complete-with-real-coords',
      input: {
        state: 'complete',
        seed: seedFromString('okumikawa-loop'),
        points: pointsFromCoords([
          { lat: 35.222, lng: 137.658 }, // 茶臼山
          { lat: 35.128, lng: 137.556 },
          { lat: 35.089, lng: 137.492 },
          { lat: 35.132, lng: 137.412 },
          { lat: 35.246, lng: 137.501 },
        ]),
      } as const,
    },
  ];

  for (const f of FIXTURES) {
    it(`fixture: ${f.name}`, () => {
      const cmds = buildCrestCommands(f.input);
      expect(cmds).toMatchSnapshot();
    });
  }

  it('SVG 出力も安定している', () => {
    const cmds = buildCrestCommands({ state: 'complete', seed: 7731 });
    const svg = crestToSvg(cmds, {
      size: 180,
      colors: { ...CREST_COLORS.light, accent: '#B5493A' },
    });
    expect(svg.startsWith('<svg')).toBe(true);
    expect(svg).toMatchSnapshot();
  });
});
