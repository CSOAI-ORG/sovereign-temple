import { defineRouting } from 'next-intl/routing';
import { LOCALES, DEFAULT_LOCALE } from './config';

export const routing = defineRouting({
  locales: LOCALES as unknown as string[],
  defaultLocale: DEFAULT_LOCALE,
  localePrefix: "never",
});
