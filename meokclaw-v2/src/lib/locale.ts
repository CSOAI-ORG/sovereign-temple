import { useLocale } from 'next-intl';
import { Locale, LOCALE_METADATA } from '@/i18n/config';

export function useLocaleMeta() {
  const locale = useLocale() as Locale;
  return LOCALE_METADATA[locale] ?? LOCALE_METADATA.en;
}

export function useIsRTL(): boolean {
  const meta = useLocaleMeta();
  return meta.dir === 'rtl';
}

export function useCurrencySymbol(): string {
  const meta = useLocaleMeta();
  return meta.currencySymbol;
}

export function formatCurrency(amount: number, locale: Locale, currency: string): string {
  try {
    return new Intl.NumberFormat(locale.replace('zh-Hant', 'zh-TW'), {
      style: 'currency',
      currency,
      minimumFractionDigits: currency === 'JPY' || currency === 'KRW' || currency === 'VND' || currency === 'IDR' ? 0 : 2,
      maximumFractionDigits: currency === 'JPY' || currency === 'KRW' || currency === 'VND' || currency === 'IDR' ? 0 : 6,
    }).format(amount);
  } catch {
    return `$${amount.toFixed(4)}`;
  }
}

export function formatNumber(n: number, locale: Locale): string {
  try {
    return new Intl.NumberFormat(locale.replace('zh-Hant', 'zh-TW')).format(n);
  } catch {
    return n.toLocaleString();
  }
}

export function formatDate(d: Date | string, locale: Locale, options?: Intl.DateTimeFormatOptions): string {
  const date = typeof d === 'string' ? new Date(d) : d;
  try {
    return new Intl.DateTimeFormat(locale.replace('zh-Hant', 'zh-TW'), {
      dateStyle: 'medium',
      timeStyle: 'short',
      ...options,
    }).format(date);
  } catch {
    return date.toLocaleString();
  }
}

export function formatRelativeTime(ms: number, locale: Locale): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  const rtf = new Intl.RelativeTimeFormat(locale.replace('zh-Hant', 'zh-TW'), { numeric: 'auto' });

  if (hours > 0) return rtf.format(-hours, 'hour');
  if (minutes > 0) return rtf.format(-minutes, 'minute');
  return rtf.format(-seconds, 'second');
}
