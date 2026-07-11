/**
 * デザイントークン（TS側）
 * Canvas/SVG 描画など CSS 変数を参照できない文脈で使う定数。
 * 値は tokens.css と必ず一致させること（単一の出典は DESIGN_PROPOSAL.md §3）。
 */

export type HobbyCategory =
  | 'touring'
  | 'cafe'
  | 'sauna'
  | 'photo'
  | 'history'
  | 'nature'
  | 'food'
  | 'art';

export interface CategoryToken {
  /** 和名（UI 表示・凡例用） */
  waName: string;
  /** 日本語ラベル */
  label: string;
  /** chip・線の色 */
  chip: string;
  /** 紙(ライト)上の文字色 */
  text: string;
  /** 藍墨(ダーク)上の文字色 */
  textDark: string;
}

export const CATEGORY_TOKENS: Record<HobbyCategory, CategoryToken> = {
  touring: { waName: '縹',   label: 'ツーリング',   chip: '#2166A6', text: '#1A4E7F', textDark: '#7FB3E6' },
  cafe:    { waName: '琥珀', label: 'カフェ巡り',   chip: '#A86A1F', text: '#7F4F14', textDark: '#DBA64E' },
  sauna:   { waName: '浅葱', label: 'サウナ',       chip: '#0F8196', text: '#0B6072', textDark: '#4FC3D6' },
  photo:   { waName: '躑躅', label: '写真',         chip: '#B8447F', text: '#8C3361', textDark: '#E58BBB' },
  history: { waName: '弁柄', label: '歴史・街道',   chip: '#A24328', text: '#79301C', textDark: '#E0876C' },
  nature:  { waName: '苔',   label: '自然・渓谷',   chip: '#4F7C3A', text: '#3A5C2B', textDark: '#8FC06E' },
  food:    { waName: '山吹', label: 'ローカル飯',   chip: '#C69211', text: '#8F6A0C', textDark: '#E6C05A' },
  art:     { waName: '桔梗', label: 'アート・工芸', chip: '#6A4F9E', text: '#4F3A78', textDark: '#B39AE0' },
};

export const BASE_TOKENS = {
  light: {
    paper: '#FAF8F3',
    paper2: '#F2EEE3',
    paper3: '#EAE4D5',
    ink: '#1C1F26',
    inkSoft: '#3D424E',
    line: '#DCD6C9',
    lineStrong: '#C3BBA9',
    ai: '#2A4B7C',
    shu: '#B5493A',
  },
  dark: {
    paper: '#14171E',
    paper2: '#1B1F28',
    paper3: '#222834',
    ink: '#EDE7DA',
    inkSoft: '#B7B1A3',
    line: '#2A303B',
    lineStrong: '#3A424F',
    ai: '#7BA7D9',
    shu: '#E07A5F',
  },
} as const;

export type ThemeName = keyof typeof BASE_TOKENS;
