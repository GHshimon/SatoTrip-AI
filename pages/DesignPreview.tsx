/**
 * DesignPreview — デザインシステムのレビュー用ショーケース（開発者向け）
 * #/design-preview で閲覧。新コンポーネントの見た目と4状態をまとめて確認する。
 */
import React, { useState } from 'react';
import RouteCrest from '../components/RouteCrest';
import WeavingLoader from '../components/design/WeavingLoader';
import { BRAND_SEED, seedFromString, pointsFromCoords, CrestState } from '../src/design/crest';
import { CATEGORY_TOKENS, HobbyCategory } from '../src/design/tokens';

const SAMPLE_POINTS = pointsFromCoords([
  { lat: 35.222, lng: 137.658 },
  { lat: 35.128, lng: 137.556 },
  { lat: 35.089, lng: 137.492 },
  { lat: 35.132, lng: 137.412 },
  { lat: 35.246, lng: 137.501 },
]);

const STATES: { state: CrestState; label: string; note: string }[] = [
  { state: 'brand', label: 'brand', note: '公式紋章（固定シード）' },
  { state: 'empty', label: 'empty', note: 'プラン0件の空状態' },
  { state: 'draft', label: 'draft', note: '下書き（破線・未確定）' },
  { state: 'complete', label: 'complete', note: '刻印済み（実座標）' },
];

export const DesignPreview: React.FC = () => {
  const [dark, setDark] = useState(false);
  const theme = dark ? 'dark' : 'light';

  const section: React.CSSProperties = { marginBottom: 48 };
  const h2: React.CSSProperties = {
    fontFamily: 'var(--st-serif)', fontSize: 22, fontWeight: 600,
    borderBottom: '1px solid var(--st-line)', paddingBottom: 8, marginBottom: 20,
  };

  return (
    <div
      className={dark ? 'st-theme-dark' : undefined}
      style={{
        background: 'var(--st-paper)', color: 'var(--st-ink)',
        fontFamily: 'var(--st-gothic)', minHeight: '100vh',
        padding: '40px clamp(18px, 4vw, 60px)',
      }}
    >
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 32 }}>
          <h1 style={{ fontFamily: 'var(--st-serif)', fontSize: 28, fontWeight: 600, margin: 0 }}>
            Design Preview <small style={{ fontSize: 12, color: 'var(--st-ink-soft)' }}>旅の同人誌 × 地形図</small>
          </h1>
          <button
            onClick={() => setDark(!dark)}
            style={{
              cursor: 'pointer', padding: '6px 16px', borderRadius: 999,
              border: '1px solid var(--st-line-strong)', background: 'transparent', color: 'var(--st-ink)',
            }}
          >
            ◐ {dark ? 'ダーク' : 'ライト'}
          </button>
        </div>

        <section style={section}>
          <h2 style={h2}>RouteCrest — 4状態</h2>
          <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
            {STATES.map(({ state, label, note }) => (
              <figure key={state} style={{ margin: 0, textAlign: 'center' }}>
                <RouteCrest
                  state={state}
                  seed={state === 'brand' ? BRAND_SEED : seedFromString('okumikawa-loop')}
                  points={state === 'complete' ? SAMPLE_POINTS : undefined}
                  accent={state === 'brand' || state === 'empty' ? undefined : CATEGORY_TOKENS.touring.chip}
                  size={170}
                  theme={theme}
                />
                <figcaption style={{ fontSize: 12, color: 'var(--st-ink-soft)', marginTop: 6 }}>
                  <b style={{ color: 'var(--st-ink)' }}>{label}</b> — {note}
                </figcaption>
              </figure>
            ))}
          </div>
        </section>

        <section style={section}>
          <h2 style={h2}>WeavingLoader — 生成待ち</h2>
          <div style={{ display: 'flex', gap: 40, alignItems: 'center', flexWrap: 'wrap' }}>
            <WeavingLoader size={240} theme={theme} />
            <p style={{ maxWidth: '38ch', fontSize: 13, color: 'var(--st-ink-soft)', lineHeight: 1.9 }}>
              AI生成の待ち時間に表示。趣味の和色の緯糸が一本ずつ織られ、朱の杼が走る。
              prefers-reduced-motion では完成形を静止表示。
            </p>
          </div>
        </section>

        <section style={section}>
          <h2 style={h2}>和色カテゴリトークン</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 10 }}>
            {(Object.keys(CATEGORY_TOKENS) as HobbyCategory[]).map((key) => {
              const c = CATEGORY_TOKENS[key];
              return (
                <div
                  key={key}
                  style={{
                    border: '1px solid var(--st-line)', borderRadius: 4, padding: '12px 14px',
                    display: 'flex', alignItems: 'center', gap: 12, background: 'var(--st-paper-2)',
                  }}
                >
                  <span style={{ width: 26, height: 26, borderRadius: '50%', background: c.chip, flexShrink: 0 }} />
                  <span style={{ fontSize: 12 }}>
                    <b style={{ color: dark ? c.textDark : c.text }}>{c.waName}</b> {c.label}
                    <br />
                    <code style={{ fontSize: 10, color: 'var(--st-ink-soft)' }}>{c.chip}</code>
                  </span>
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
};

export default DesignPreview;
