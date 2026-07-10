/** @type {import('tailwindcss').Config} */
// index.html にインラインで書かれていた Play CDN 用設定をそのまま移植したもの。
// 値を変える場合はデザイントークン導入(ui-redesign)側で行う。
export default {
  darkMode: 'class',
  content: [
    './index.html',
    './*.{ts,tsx}',
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#FF6B6B',
        secondary: '#FFD166',
        accent: '#4D96FF',
        background: {
          light: '#F8F9FC',
          dark: '#1A1C2C',
        },
        card: {
          light: '#FFFFFF',
          dark: '#27293D',
        },
        text: {
          light: '#2D3748',
          dark: '#E2E8F0',
          muted: '#718096',
        },
      },
    },
  },
  plugins: [],
}
