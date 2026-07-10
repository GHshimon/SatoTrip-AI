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
