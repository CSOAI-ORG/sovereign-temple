import { getRequestConfig } from 'next-intl/server';
import { routing } from './routing';

export const LOCALES = [
  'en',      // English
  'zh',      // Chinese Simplified
  'zh-Hant', // Chinese Traditional
  'ko',      // Korean
  'ja',      // Japanese
  'es',      // Spanish
  'pt',      // Portuguese
  'ar',      // Arabic (RTL)
  'hi',      // Hindi
  'fr',      // French
  'de',      // German
  'ru',      // Russian
  'id',      // Indonesian
  'vi',      // Vietnamese
  'th',      // Thai
] as const;

export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = 'en';

export const LOCALE_METADATA: Record<Locale, {
  label: string;
  nativeLabel: string;
  dir: 'ltr' | 'rtl';
  fontFamily: string;
  currency: string;
  currencySymbol: string;
  theme: string;
}> = {
  en:      { label: 'English',      nativeLabel: 'English',      dir: 'ltr', fontFamily: 'var(--font-sans)',    currency: 'USD', currencySymbol: '$',  theme: 'western' },
  zh:      { label: 'Chinese (Simplified)',  nativeLabel: '简体中文',     dir: 'ltr', fontFamily: 'var(--font-chinese)', currency: 'CNY', currencySymbol: '¥',  theme: 'china' },
  'zh-Hant': { label: 'Chinese (Traditional)', nativeLabel: '繁體中文',     dir: 'ltr', fontFamily: 'var(--font-chinese)', currency: 'CNY', currencySymbol: 'NT$', theme: 'china' },
  ko:      { label: 'Korean',       nativeLabel: '한국어',        dir: 'ltr', fontFamily: 'var(--font-korean)',  currency: 'KRW', currencySymbol: '₩',  theme: 'korea' },
  ja:      { label: 'Japanese',     nativeLabel: '日本語',        dir: 'ltr', fontFamily: 'var(--font-japanese)', currency: 'JPY', currencySymbol: '¥',  theme: 'japan' },
  es:      { label: 'Spanish',      nativeLabel: 'Español',      dir: 'ltr', fontFamily: 'var(--font-sans)',    currency: 'EUR', currencySymbol: '€',  theme: 'western' },
  pt:      { label: 'Portuguese',   nativeLabel: 'Português',    dir: 'ltr', fontFamily: 'var(--font-sans)',    currency: 'EUR', currencySymbol: '€',  theme: 'western' },
  ar:      { label: 'Arabic',       nativeLabel: 'العربية',      dir: 'rtl', fontFamily: 'var(--font-arabic)',  currency: 'SAR', currencySymbol: '﷼',  theme: 'arabia' },
  hi:      { label: 'Hindi',        nativeLabel: 'हिन्दी',       dir: 'ltr', fontFamily: 'var(--font-hindi)',   currency: 'INR', currencySymbol: '₹',  theme: 'india' },
  fr:      { label: 'French',       nativeLabel: 'Français',     dir: 'ltr', fontFamily: 'var(--font-sans)',    currency: 'EUR', currencySymbol: '€',  theme: 'western' },
  de:      { label: 'German',       nativeLabel: 'Deutsch',      dir: 'ltr', fontFamily: 'var(--font-sans)',    currency: 'EUR', currencySymbol: '€',  theme: 'western' },
  ru:      { label: 'Russian',      nativeLabel: 'Русский',      dir: 'ltr', fontFamily: 'var(--font-sans)',    currency: 'RUB', currencySymbol: '₽',  theme: 'western' },
  id:      { label: 'Indonesian',   nativeLabel: 'Bahasa Indonesia', dir: 'ltr', fontFamily: 'var(--font-sans)', currency: 'IDR', currencySymbol: 'Rp', theme: 'western' },
  vi:      { label: 'Vietnamese',   nativeLabel: 'Tiếng Việt',   dir: 'ltr', fontFamily: 'var(--font-sans)',    currency: 'VND', currencySymbol: '₫',  theme: 'western' },
  th:      { label: 'Thai',         nativeLabel: 'ไทย',          dir: 'ltr', fontFamily: 'var(--font-thai)',    currency: 'THB', currencySymbol: '฿',  theme: 'western' },
};

export const RTL_LOCALES: Locale[] = LOCALES.filter((l) => LOCALE_METADATA[l].dir === 'rtl');

export default getRequestConfig(async () => {
  // Hardcoded for static export — avoids headers() dynamic rendering
  const locale: Locale = 'en';

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
    timeZone: 'UTC',
    now: new Date(),
  };
});
