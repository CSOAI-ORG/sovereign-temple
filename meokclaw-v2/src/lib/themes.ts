import { Locale } from '@/i18n/config';

export interface CulturalTheme {
  primary: string;
  primaryDim: string;
  accent: string;
  success: string;
  warning: string;
  danger: string;
  background: string;
  surface: string;
  surfaceRaised: string;
  foreground: string;
  muted: string;
  border: string;
  fontFamily: string;
  lineHeight: number;
  letterSpacing: string;
  density: 'compact' | 'normal' | 'spacious';
}

const THEMES: Record<string, CulturalTheme> = {
  western: {
    primary: '#3b82f6',
    primaryDim: '#2563eb',
    accent: '#8b5cf6',
    success: '#22c55e',
    warning: '#f59e0b',
    danger: '#ef4444',
    background: '#0a0a0f',
    surface: '#111118',
    surfaceRaised: '#1a1a24',
    foreground: '#e4e4e7',
    muted: '#71717a',
    border: '#27272a',
    fontFamily: 'var(--font-sans)',
    lineHeight: 1.6,
    letterSpacing: '0em',
    density: 'normal',
  },
  china: {
    primary: '#dc2626',
    primaryDim: '#b91c1c',
    accent: '#f59e0b',
    success: '#dc2626',
    warning: '#f97316',
    danger: '#991b1b',
    background: '#0a0a0f',
    surface: '#111118',
    surfaceRaised: '#1a1a24',
    foreground: '#e4e4e7',
    muted: '#71717a',
    border: '#27272a',
    fontFamily: 'var(--font-chinese)',
    lineHeight: 1.7,
    letterSpacing: '0.02em',
    density: 'compact',
  },
  korea: {
    primary: '#1e40af',
    primaryDim: '#1e3a8a',
    accent: '#c026d3',
    success: '#16a34a',
    warning: '#f59e0b',
    danger: '#dc2626',
    background: '#0a0a0f',
    surface: '#111118',
    surfaceRaised: '#1a1a24',
    foreground: '#e4e4e7',
    muted: '#71717a',
    border: '#27272a',
    fontFamily: 'var(--font-korean)',
    lineHeight: 1.65,
    letterSpacing: '-0.01em',
    density: 'normal',
  },
  japan: {
    primary: '#b91c1c',
    primaryDim: '#991b1b',
    accent: '#374151',
    success: '#f9fafb',
    warning: '#f59e0b',
    danger: '#111827',
    background: '#0a0a0f',
    surface: '#111118',
    surfaceRaised: '#1a1a24',
    foreground: '#e4e4e7',
    muted: '#71717a',
    border: '#27272a',
    fontFamily: 'var(--font-japanese)',
    lineHeight: 1.8,
    letterSpacing: '0.03em',
    density: 'spacious',
  },
  arabia: {
    primary: '#16a34a',
    primaryDim: '#15803d',
    accent: '#0d9488',
    success: '#16a34a',
    warning: '#f59e0b',
    danger: '#dc2626',
    background: '#0a0a0f',
    surface: '#111118',
    surfaceRaised: '#1a1a24',
    foreground: '#e4e4e7',
    muted: '#71717a',
    border: '#27272a',
    fontFamily: 'var(--font-arabic)',
    lineHeight: 1.9,
    letterSpacing: '0em',
    density: 'spacious',
  },
  india: {
    primary: '#f97316',
    primaryDim: '#ea580c',
    accent: '#06b6d4',
    success: '#22c55e',
    warning: '#f59e0b',
    danger: '#ef4444',
    background: '#0a0a0f',
    surface: '#111118',
    surfaceRaised: '#1a1a24',
    foreground: '#e4e4e7',
    muted: '#71717a',
    border: '#27272a',
    fontFamily: 'var(--font-hindi)',
    lineHeight: 1.8,
    letterSpacing: '0.01em',
    density: 'normal',
  },
};

const LOCALE_THEME_MAP: Record<Locale, string> = {
  en: 'western', 'zh': 'china', 'zh-Hant': 'china', ko: 'korea',
  ja: 'japan', es: 'western', pt: 'western', ar: 'arabia',
  hi: 'india', fr: 'western', de: 'western', ru: 'western',
  id: 'western', vi: 'western', th: 'western',
};

export function getThemeForLocale(locale: Locale): CulturalTheme {
  const key = LOCALE_THEME_MAP[locale] ?? 'western';
  return THEMES[key] ?? THEMES.western;
}

export function applyThemeToDocument(theme: CulturalTheme) {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  root.style.setProperty('--primary', theme.primary);
  root.style.setProperty('--primary-dim', theme.primaryDim);
  root.style.setProperty('--accent', theme.accent);
  root.style.setProperty('--success', theme.success);
  root.style.setProperty('--warning', theme.warning);
  root.style.setProperty('--danger', theme.danger);
  root.style.setProperty('--font-family', theme.fontFamily);
  root.style.setProperty('--line-height', String(theme.lineHeight));
  root.style.setProperty('--letter-spacing', theme.letterSpacing);
}
