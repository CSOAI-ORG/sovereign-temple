import createMiddleware from 'next-intl/middleware';
import { routing } from './i18n/routing';

export default createMiddleware(routing);

export const config = {
  matcher: [
    '/',
    '/(zh|zh-Hant|ko|ja|es|pt|ar|hi|fr|de|ru|id|vi|th|en)/:path*',
  ],
};
