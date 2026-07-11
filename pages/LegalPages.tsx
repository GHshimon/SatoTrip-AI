import React from 'react';

// 共通レイアウト（法務・情報ページ用）
const LegalLayout: React.FC<{
  title: string;
  onNavigate: (path: string) => void;
  children: React.ReactNode;
}> = ({ title, onNavigate, children }) => (
  <div className="max-w-3xl mx-auto px-4 py-12">
    <button
      onClick={() => onNavigate('/')}
      className="text-text-muted hover:text-primary text-sm flex items-center gap-1 mb-6"
    >
      <span className="material-symbols-outlined text-base">arrow_back</span> トップへ戻る
    </button>
    <h1 className="text-3xl font-bold mb-8">{title}</h1>
    <div className="space-y-6 text-text-light leading-relaxed">{children}</div>
  </div>
);

const Section: React.FC<{ heading: string; children: React.ReactNode }> = ({ heading, children }) => (
  <section>
    <h2 className="text-lg font-bold mb-2">{heading}</h2>
    <div className="text-text-muted space-y-2">{children}</div>
  </section>
);

// 運営者が確定させるべき箇所のプレースホルダ。公開前に実際の値へ差し替えること。
const PLACEHOLDER = '（運営者情報を記入してください）';

// ─────────────────────────────────────────────────────────────
// 運営者情報（記入はこのブロックだけでよい。各ページへ自動反映される）
// 個人事業主の場合、所在地・電話番号は消費者庁の解釈により
// 「請求があれば遅滞なく開示する」旨の記載で代替できる（下の既定値）。
// 自宅住所等を公開したくない場合は既定値のままでよいが、
// 開示請求を受けたら実際に遅滞なく開示する運用が条件。
// ─────────────────────────────────────────────────────────────
const OPERATOR = {
  /** 販売事業者（個人の場合は戸籍上の氏名。屋号のみは不可） */
  seller: PLACEHOLDER,
  /** 運営統括責任者（個人事業主なら販売事業者と同じ氏名でよい） */
  manager: PLACEHOLDER,
  /** 所在地 */
  address: 'ご請求をいただければ遅滞なく開示いたします。開示をご希望の場合は、下記メールアドレスまでご請求ください。',
  /** 電話番号 */
  phone: 'ご請求をいただければ遅滞なく開示いたします。開示をご希望の場合は、下記メールアドレスまでご請求ください。',
  /** お問い合わせ用メールアドレス */
  email: PLACEHOLDER,
  /** お問い合わせ受付時間（例: 平日 10:00〜18:00（土日祝を除く）） */
  contactHours: PLACEHOLDER,
} as const;

// 利用規約・プライバシーポリシーの制定日（内容を改定したらここを更新する）
const LEGAL_REVISION_DATE = '2026年7月11日';

export const TermsOfService: React.FC<{ onNavigate: (path: string) => void }> = ({ onNavigate }) => (
  <LegalLayout title="利用規約" onNavigate={onNavigate}>
    <p className="text-text-muted">
      本利用規約（以下「本規約」）は、SatoTrip AI（以下「本サービス」）の利用条件を定めるものです。
      利用者は、本規約に同意のうえ本サービスを利用するものとします。
    </p>
    <Section heading="第1条（適用）">
      <p>本規約は、利用者と本サービス運営者との間の本サービスの利用に関わる一切の関係に適用されます。</p>
    </Section>
    <Section heading="第2条（アカウント）">
      <p>利用者は、自己の責任においてアカウント情報を管理するものとし、第三者に利用させてはなりません。</p>
    </Section>
    <Section heading="第3条（AIが生成する旅行プランについて）">
      <p>
        本サービスが提供する旅行プラン・スポット情報・所要時間・ルート等は、AIおよび外部データに基づく
        参考情報です。営業時間・料金・実在性等は変動する場合があり、内容の正確性・完全性を保証するもの
        ではありません。利用者は、実際の訪問前に各施設の公式情報をご確認ください。
      </p>
    </Section>
    <Section heading="第4条（禁止事項）">
      <p>法令または公序良俗に違反する行為、本サービスの運営を妨害する行為等を禁止します。</p>
    </Section>
    <Section heading="第5条（免責事項）">
      <p>
        本サービスの利用または利用不能により利用者に生じた損害について、運営者は法令で許容される範囲で
        責任を負いません。
      </p>
    </Section>
    <Section heading="第6条（規約の変更）">
      <p>運営者は、必要と判断した場合、利用者への通知のうえ本規約を変更できるものとします。</p>
    </Section>
    <p className="text-sm text-text-muted pt-4">最終改定日: {LEGAL_REVISION_DATE}</p>
  </LegalLayout>
);

export const PrivacyPolicy: React.FC<{ onNavigate: (path: string) => void }> = ({ onNavigate }) => (
  <LegalLayout title="プライバシーポリシー" onNavigate={onNavigate}>
    <p className="text-text-muted">
      本サービスは、利用者の個人情報を以下の方針に基づき適切に取り扱います。
    </p>
    <Section heading="1. 取得する情報">
      <p>
        アカウント登録情報（ユーザー名・メールアドレス等）、作成された旅行プラン、
        サービス利用に伴い自動的に取得されるログ情報を取得します。
      </p>
    </Section>
    <Section heading="2. 利用目的">
      <p>本サービスの提供・維持・改善、本人確認、問い合わせ対応のために利用します。</p>
    </Section>
    <Section heading="3. 第三者提供">
      <p>法令に基づく場合を除き、本人の同意なく個人情報を第三者に提供しません。</p>
    </Section>
    <Section heading="4. 外部サービス">
      <p>
        旅行プラン生成やホテル検索等のために、外部のAI・地図・予約サービスと連携する場合があります。
        連携先での情報の取り扱いは各社のポリシーに従います。
      </p>
    </Section>
    <Section heading="5. 開示・訂正・削除の請求">
      <p>利用者は、自己の個人情報について開示・訂正・削除を請求できます。下記のお問い合わせ窓口までご連絡ください。</p>
    </Section>
    <Section heading="6. お問い合わせ窓口">
      <p>メール: {OPERATOR.email}</p>
    </Section>
    <p className="text-sm text-text-muted pt-4">最終改定日: {LEGAL_REVISION_DATE}</p>
  </LegalLayout>
);

// 特定商取引法に基づく表記（有料サービス提供時は法律上の必須項目。運営者が実値を記入すること）
export const CommercialTransactionAct: React.FC<{ onNavigate: (path: string) => void }> = ({ onNavigate }) => (
  <LegalLayout title="特定商取引法に基づく表記" onNavigate={onNavigate}>
    <p className="text-text-muted">
      有料プランを提供する場合、以下の項目は特定商取引法により表示が義務付けられています。
      公開前に実際の情報を必ず記入してください。
    </p>
    <div className="border border-gray-200 rounded-lg divide-y">
      {[
        ['販売事業者', OPERATOR.seller],
        ['運営統括責任者', OPERATOR.manager],
        ['所在地', OPERATOR.address],
        ['電話番号', OPERATOR.phone],
        ['メールアドレス', OPERATOR.email],
        ['販売価格', '各プランの購入画面に表示します（ベーシック: 月額980円、プレミアム: 月額2,980円。いずれも税込）'],
        ['商品代金以外の必要料金', 'インターネット接続にかかる通信料等は、お客様のご負担となります。'],
        ['お支払い方法', 'クレジットカード決済（Stripe）'],
        ['お支払い時期', 'お申し込み時に初回分を決済し、以後1か月ごとの更新日に自動決済されます。'],
        ['サービス提供時期', 'お支払い手続き完了後、直ちにご利用いただけます'],
        [
          '解約方法・解約期限',
          '設定画面の「お支払い・ご契約」→「契約を管理」からいつでも解約できます。次回更新日の前までに解約手続きを行うと、次回以降の請求は発生しません。',
        ],
        [
          '返品・キャンセルについて',
          'デジタルサービスの性質上、決済完了後の返金には応じられません。解約後も、お支払い済みの請求期間の末日まではサービスをご利用いただけます。',
        ],
      ].map(([label, value]) => (
        <div key={label} className="grid grid-cols-3 gap-2 p-4 text-sm">
          <div className="font-bold text-text-light col-span-1">{label}</div>
          <div className="text-text-muted col-span-2">{value}</div>
        </div>
      ))}
    </div>
  </LegalLayout>
);

export const Contact: React.FC<{ onNavigate: (path: string) => void }> = ({ onNavigate }) => (
  <LegalLayout title="お問い合わせ" onNavigate={onNavigate}>
    <p className="text-text-muted">
      本サービスに関するご質問・ご要望は、以下の窓口までご連絡ください。
    </p>
    <Section heading="お問い合わせ窓口">
      <p>メール: {OPERATOR.email}</p>
      <p>受付時間: {OPERATOR.contactHours}</p>
    </Section>
    <p className="text-sm text-text-muted pt-4">
      ※ お問い合わせフォームは今後提供予定です。現時点では上記メール窓口をご利用ください。
    </p>
  </LegalLayout>
);
