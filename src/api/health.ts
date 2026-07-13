/**
 * バックエンドの事前ウォームアップ
 *
 * 無料枠のバックエンド（Render）は15分無アクセスでスリープし、次のリクエストで
 * 起動（コールドスタート）に30〜60秒かかる。プラン生成は元々60〜70秒かかるため、
 * スリープ中に生成を投げると「起動＋生成」でタイムアウトしやすい。
 *
 * そこで作成画面を開いた時点で /health を fire-and-forget で叩き、ユーザーが入力
 * している間にサーバーを起こしておく。送信時には温まった状態で生成だけを待てばよい。
 */
import { apiClient } from './client';

// 短時間に何度も叩かないためのフラグ（画面の再マウントや連続遷移での多重pingを抑止）
let warmedRecently = false;

/** バックエンドを事前に起こす（認証不要・レスポンスは使わない・失敗は無視） */
export function warmupBackend(): void {
  if (warmedRecently) return;
  warmedRecently = true;
  // 一定時間後に再度許可（起動維持には十分な間隔）
  setTimeout(() => { warmedRecently = false; }, 60000);
  try {
    const url = `${apiClient.getBaseURL()}/health`;
    // keepalive: ページ遷移・離脱があっても送信を継続させる
    fetch(url, { method: 'GET', keepalive: true }).catch(() => {
      // スリープからの起動中は失敗し得るが、目的は「起こす」ことなので握りつぶす
    });
  } catch {
    // ネットワーク未接続等でも画面表示を妨げない
  }
}
