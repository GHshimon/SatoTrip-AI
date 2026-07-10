/**
 * LandingPage — 新デザイン「旅の同人誌 × 地形図」のランディング
 *
 * 新デザイン第1画面(DESIGN_PROPOSAL §8-3)。旧 Layout に依存せず自前のヘッダを持つ。
 * ダーク切替はこの画面のみ(.st-theme-dark / §7.4)。既存画面には影響しない。
 */
import React, { useState } from 'react';
import TopoContour from '../components/design/TopoContour';
import RouteCrest from '../components/RouteCrest';
import { BRAND_SEED } from '../src/design/crest';
import { CATEGORY_TOKENS, HobbyCategory } from '../src/design/tokens';

const CATEGORY_NOTES: Record<HobbyCategory, string> = {
  touring: '峠・湧水・道の駅',
  cafe: '焙煎所・器・古民家',
  sauna: '外気浴・水風呂・整い',
  photo: '黄金時間・棚田・廃線',
  history: '宿場・城下・古社',
  nature: '苔・滝・原生林',
  food: '郷土食・名水・市場',
  art: '窯元・美術館・工房',
};

const CATEGORY_ORDER: HobbyCategory[] = [
  'touring', 'cafe', 'sauna', 'photo', 'history', 'nature', 'food', 'art',
];

interface LandingPageProps {
  onNavigate: (path: string) => void;
  isAuthenticated: boolean;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onNavigate, isAuthenticated }) => {
  const [dark, setDark] = useState(false);
  const theme = dark ? 'dark' : 'light';

  return (
    <div
      className={dark ? 'st-theme-dark' : undefined}
      style={{
        background: 'var(--st-paper)',
        color: 'var(--st-ink)',
        fontFamily: 'var(--st-gothic)',
        minHeight: '100vh',
      }}
    >
      {/* ---------- header ---------- */}
      <header
        style={{
          position: 'relative',
          zIndex: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px clamp(18px, 4vw, 44px)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, fontFamily: 'var(--st-serif)', fontSize: 21, letterSpacing: '0.06em' }}>
          SatoTrip<span style={{ color: 'var(--st-shu)' }}>.</span>
          <small style={{ fontFamily: 'var(--st-gothic)', fontSize: 10, letterSpacing: '0.22em', color: 'var(--st-ink-soft)' }}>
            里 を 旅 す る
          </small>
        </div>
        <nav style={{ display: 'flex', alignItems: 'center', gap: 22, fontSize: 13, color: 'var(--st-ink-soft)' }}>
          <button onClick={() => onNavigate('/plans')} className="st-navlink">プラン一覧</button>
          <button onClick={() => onNavigate('/myspots')} className="st-navlink">マイスポット</button>
          <button
            onClick={() => setDark(!dark)}
            aria-label="テーマ切替"
            style={{
              cursor: 'pointer', width: 34, height: 34, borderRadius: '50%',
              border: '1px solid var(--st-line-strong)', background: 'transparent',
              color: 'var(--st-ink)', fontSize: 14,
            }}
          >
            ◐
          </button>
          <button
            onClick={() => onNavigate(isAuthenticated ? '/create' : '/login')}
            style={{
              cursor: 'pointer', padding: '8px 18px', borderRadius: 999,
              border: '1px solid var(--st-ink)', background: 'transparent',
              color: 'var(--st-ink)', fontSize: 13, letterSpacing: '0.08em',
              transition: 'all var(--st-dur-micro)',
            }}
          >
            はじめる
          </button>
        </nav>
      </header>

      {/* ---------- hero ---------- */}
      <section
        style={{
          position: 'relative',
          minHeight: 'calc(100vh - 70px)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '40px clamp(18px, 4vw, 44px) 80px',
          overflow: 'hidden',
        }}
      >
        <TopoContour seed={3157} />
        {/* テキスト可読性のスクリム */}
        <div
          aria-hidden="true"
          style={{
            position: 'absolute', inset: 0, pointerEvents: 'none',
            background: `radial-gradient(110% 90% at 18% 45%, ${dark ? 'rgba(20,23,30,0.75)' : 'rgba(250,248,243,0.78)'} 0%, rgba(0,0,0,0) 62%)`,
          }}
        />
        <div style={{ position: 'relative', maxWidth: 1180, margin: '0 auto', width: '100%' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 12, fontSize: 12, letterSpacing: '0.24em', color: 'var(--st-ai)', marginBottom: 24 }}>
            <span style={{ width: 46, height: 1, background: 'var(--st-ai)', opacity: 0.6 }} />
            趣味 × 地元インサイダー
          </div>
          <h1
            style={{
              fontFamily: 'var(--st-serif)', fontWeight: 600,
              fontSize: 'clamp(34px, 6.6vw, 80px)', lineHeight: 1.3,
              letterSpacing: '0.02em', margin: 0,
            }}
          >
            地図に載らない、
            <br />
            あなただけの<span style={{ color: 'var(--st-shu)' }}>里</span>を旅する。
          </h1>
          <p style={{ maxWidth: '44ch', marginTop: 26, fontSize: 'clamp(14px, 1.6vw, 17px)', color: 'var(--st-ink-soft)', lineHeight: 1.9 }}>
            ツーリングも、カフェ巡りも、サウナも。趣味の解像度で全国を検索し、
            地元の人しか知らない一日を、一冊のしおりに編みます。
          </p>
          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginTop: 34 }}>
            <button
              onClick={() => onNavigate('/create')}
              style={{
                cursor: 'pointer', padding: '14px 28px', borderRadius: 999, border: 'none',
                background: 'var(--st-shu)', color: '#fff', fontSize: 14, letterSpacing: '0.06em',
                boxShadow: '0 10px 30px -12px var(--st-shu)',
                transition: 'transform var(--st-dur-micro) var(--st-ease)',
              }}
            >
              プランを編みはじめる →
            </button>
            <button
              onClick={() => onNavigate('/plans')}
              style={{
                cursor: 'pointer', padding: '14px 28px', borderRadius: 999,
                border: '1px solid var(--st-line-strong)', background: 'transparent',
                color: 'var(--st-ink)', fontSize: 14, letterSpacing: '0.06em',
              }}
            >
              みんなのプランを見る
            </button>
          </div>
        </div>
        {/* ブランド紋章 = 隅の刻印 */}
        <div style={{ position: 'absolute', right: 'clamp(16px, 5vw, 70px)', bottom: 90 }} className="st-hide-mobile">
          <RouteCrest state="brand" seed={BRAND_SEED} size={220} theme={theme} aria-label="SatoTrip 公式紋章" />
        </div>
      </section>

      {/* ---------- hobbies ---------- */}
      <section
        style={{
          position: 'relative', zIndex: 1,
          background: 'var(--st-paper-2)',
          borderTop: '1px solid var(--st-line)',
          borderBottom: '1px solid var(--st-line)',
          padding: 'clamp(56px, 8vw, 110px) clamp(18px, 4vw, 44px)',
        }}
      >
        <div style={{ maxWidth: 1180, margin: '0 auto' }}>
          <div style={{ fontSize: 12, letterSpacing: '0.24em', color: 'var(--st-shu)', marginBottom: 8 }}>01 — HOBBIES</div>
          <h2 style={{ fontFamily: 'var(--st-serif)', fontWeight: 600, fontSize: 'clamp(24px, 3.6vw, 40px)', margin: '0 0 36px' }}>
            「何をしたいか」から、旅がはじまる。
          </h2>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))',
              gap: 14,
            }}
          >
            {CATEGORY_ORDER.map((key) => {
              const cat = CATEGORY_TOKENS[key];
              return (
                <button
                  key={key}
                  onClick={() => onNavigate(`/create?hobby=${key}`)}
                  className="st-catcard"
                  style={{
                    position: 'relative', textAlign: 'left', cursor: 'pointer',
                    border: '1px solid var(--st-line-strong)', borderRadius: 4,
                    background: 'var(--st-paper)', color: 'var(--st-ink)',
                    padding: '20px 18px 16px 22px', minHeight: 120,
                    display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: 14,
                    transition: 'transform var(--st-dur-ui) var(--st-ease), box-shadow var(--st-dur-ui) var(--st-ease)',
                  }}
                >
                  <span style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 4, background: cat.chip }} />
                  <span style={{ fontSize: 10, letterSpacing: '0.22em', color: 'var(--st-ink-soft)' }}>
                    {cat.waName} ─ {key.toUpperCase()}
                  </span>
                  <span>
                    <span style={{ display: 'block', fontFamily: 'var(--st-serif)', fontSize: 20, fontWeight: 600 }}>{cat.label}</span>
                    <span style={{ fontSize: 11, color: 'var(--st-ink-soft)' }}>{CATEGORY_NOTES[key]}</span>
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* ---------- CTA ---------- */}
      <section style={{ background: 'var(--st-ai)', textAlign: 'center', padding: 'clamp(56px, 8vw, 100px) 20px' }}>
        <h2 style={{ fontFamily: 'var(--st-serif)', fontWeight: 600, color: '#fff', fontSize: 'clamp(26px, 4.2vw, 46px)', margin: '0 0 16px' }}>
          あなたの「好き」で、全国を旅しよう。
        </h2>
        <p style={{ color: 'rgba(255,255,255,0.82)', maxWidth: '40ch', margin: '0 auto 30px' }}>
          趣味を選ぶだけ。あとはSatoTripが、地元ならではの一日を一冊に編みます。
        </p>
        <button
          onClick={() => onNavigate(isAuthenticated ? '/create' : '/login')}
          style={{
            cursor: 'pointer', padding: '14px 30px', borderRadius: 999, border: 'none',
            background: '#fff', color: 'var(--st-ai)', fontSize: 14, letterSpacing: '0.06em', fontWeight: 600,
          }}
        >
          無料でしおりを作る →
        </button>
      </section>

      {/* ---------- footer ---------- */}
      <footer
        style={{
          borderTop: '1px solid var(--st-line)', padding: '36px clamp(18px, 4vw, 44px)',
          display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16,
          fontSize: 12, color: 'var(--st-ink-soft)',
        }}
      >
        <span style={{ fontFamily: 'var(--st-serif)', fontSize: 17 }}>
          SatoTrip<span style={{ color: 'var(--st-shu)' }}>.</span>
        </span>
        <span>© 2026 SatoTrip — 里を旅する。</span>
      </footer>

      <style>{`
        .st-navlink {
          background: none; border: none; cursor: pointer; font-size: 13px;
          color: var(--st-ink-soft); letter-spacing: 0.05em; padding: 0;
        }
        .st-navlink:hover { color: var(--st-ink); }
        .st-catcard:hover {
          transform: translateY(-3px);
          box-shadow: 0 20px 36px -26px rgba(0, 0, 0, 0.5);
        }
        @media (max-width: 900px) { .st-hide-mobile { display: none; } }
        @media (prefers-reduced-motion: reduce) {
          .st-catcard, .st-catcard:hover { transform: none; transition: none; }
        }
      `}</style>
    </div>
  );
};

export default LandingPage;
