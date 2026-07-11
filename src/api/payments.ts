/**
 * 決済API（Stripe）
 */
import { apiClient } from './client';

export interface PaymentConfig {
  configured: boolean;
  publishable_key: string | null;
}

export interface CheckoutSession {
  session_id: string;
  url: string;
}

/** 決済の公開設定（有効かどうか） */
export async function getPaymentConfig(): Promise<PaymentConfig> {
  return apiClient.get<PaymentConfig>('/api/payments/config');
}

/** Checkoutセッションを作成し、Stripeの決済URLを返す */
export async function createCheckout(planName: string): Promise<CheckoutSession> {
  return apiClient.post<CheckoutSession>('/api/payments/checkout', { plan_name: planName });
}

export interface BillingPortalSession {
  url: string;
}

/**
 * Stripe カスタマーポータルのURLを取得する。
 * 解約・支払方法の変更・請求履歴の確認はポータル側で行う（有料プラン契約者のみ）。
 */
export async function createBillingPortal(): Promise<BillingPortalSession> {
  return apiClient.post<BillingPortalSession>('/api/payments/portal', {});
}
