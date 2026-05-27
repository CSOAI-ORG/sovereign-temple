# MEOKCLAW i18n Architecture

> Full end-to-end internationalization across 15 languages with culture-aware UX.

## Supported Locales

| Code | Language | Script | Dir | Currency | Theme |
|------|----------|--------|-----|----------|-------|
| en | English | Latin | LTR | USD | western |
| zh | Chinese (Simplified) | Han | LTR | CNY | china |
| zh-Hant | Chinese (Traditional) | Han | LTR | CNY | china |
| ko | Korean | Hangul | LTR | KRW | korea |
| ja | Japanese | Kanji/Hiragana/Katakana | LTR | JPY | japan |
| es | Spanish | Latin | LTR | EUR | western |
| pt | Portuguese | Latin | LTR | EUR | western |
| ar | Arabic | Arabic | RTL | SAR | arabia |
| hi | Hindi | Devanagari | LTR | INR | india |
| fr | French | Latin | LTR | EUR | western |
| de | German | Latin | LTR | EUR | western |
| ru | Russian | Cyrillic | LTR | RUB | western |
| id | Indonesian | Latin | LTR | IDR | western |
| vi | Vietnamese | Latin | LTR | VND | western |
| th | Thai | Thai | LTR | THB | western |

## Architecture Layers

### Layer 1: Next.js Frontend (`next-intl`)
- **Routing:** Locale-prefixed routes (`/zh`, `/ko`, `/ar`)
- **Middleware:** Auto-detects browser locale, redirects to best match
- **Messages:** Nested JSON catalogs in `/messages/*.json`
- **RTL:** Dynamic `dir` attribute, mirrored layouts for Arabic
- **Fonts:** Per-locale font loading via CSS custom properties
- **Themes:** Cultural color psychology (red for China, saffron for India, etc.)

### Layer 2: FastAPI Backend
- **Accept-Language:** Every endpoint respects `Accept-Language` header
- **Catalogs:** Python dict catalogs in `backend/i18n/catalogs/`
- **Fallback chain:** `zh-Hant` → `zh` → `en`
- **Formatters:** `format_currency`, `format_number`, `format_date`

### Layer 3: Swift (Apple Intelligence)
- `.strings` files for 15 locales
- `LocalizedStringResource` for App Intents
- `.stringsdict` for pluralization

### Layer 4: Kotlin (Samsung/Android/China)
- `strings.xml` resources for 15 locales
- `<plurals>` support
- Knox policy descriptions localized

## Translation Catalog Structure

```json
{
  "meta": { "title": "...", "description": "..." },
  "nav": { "chat": "...", "council": "...", "arena": "..." },
  "brain": { "leftBrain": "...", "fusion": "...", "careMode": "..." },
  "chat": { "placeholder": "...", "emptyTitle": "...", "errorOffline": "..." },
  "warRoom": { "title": "...", "loading": "...", "tasks": "..." },
  "arena": { "title": "...", "runArena": "...", "voteBest": "..." },
  "errors": { "guardrailsBlocked": "...", "offline": "..." },
  "currency": { "usd": "${amount}", "cny": "¥{amount}", "krw": "₩{amount}" }
}
```

## Cultural UX

### Color Psychology
- **China (zh):** Red primary (#dc2626) — prosperity, luck
- **Korea (ko):** Blue primary (#1e40af) — Taegeukgi colors
- **Japan (ja):** Red primary (#b91c1c) — Shinto aesthetic
- **India (hi):** Saffron primary (#f97316) — Tricolor
- **Arabia (ar):** Green primary (#16a34a) — Islam

### Typography
- CJK: Noto Sans SC/TC/JP/KR with wider letter-spacing
- Arabic: Noto Sans Arabic with increased line-height
- Hindi: Noto Sans Devanagari with taller line-height
- Thai: Noto Sans Thai

### Layout
- Arabic: RTL with mirrored sidebar and icons
- CJK: Compact density preference
- Western: Normal density with more whitespace

## Quality Gates

| Gate | Target | Verification |
|------|--------|-------------|
| Coverage | 100% | `test_translations.py` |
| Hardcoded strings | 0 | `grep` scan |
| RTL rendering | Pass | Visual regression |
| Currency accuracy | 100% | `test_formatters.py` |
| Font loading | <100ms | Lighthouse |
| Bundle size | <50KB/locale | Build analysis |

## Adding a New Language

1. Add locale to `LOCALES` in `src/i18n/config.ts`
2. Add `LOCALE_METADATA` entry
3. Create `messages/<locale>.json` from `en.json`
4. Create `backend/i18n/catalogs/<locale>.json`
5. Add Swift `.strings` file
6. Add Kotlin `strings.xml`
7. Run `test_translations.py`
8. Update this doc

## Machine Translation Disclaimer

All non-English translations in this release were generated via machine translation
and marked with `machine_translated: true` metadata. Native speaker review is
strongly encouraged before production deployment.
