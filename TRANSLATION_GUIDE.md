# Translation Contribution Guide

## How to Add or Improve Translations

### For Developers

1. **Find the source of truth:** `meokclaw-v2/messages/en.json` is the master catalog.
2. **Add your locale:** Copy `en.json` to `<locale>.json`.
3. **Translate all values:** Do not leave any English strings.
4. **Test coverage:** Run `pytest tests/i18n/test_translations.py`.
5. **Submit PR:** Include screenshots of the UI in your locale.

### For Non-Technical Translators

1. Download `messages/en.json`
2. Translate all string values (keep keys exactly the same)
3. Save as `<your-locale>.json`
4. Open a GitHub issue with the file attached

### Translation Quality Checklist

- [ ] All keys from `en.json` are present
- [ ] No empty or placeholder values
- [ ] Parameterized strings preserved: `{count}`, `{amount}`, `{ms}`
- [ ] Cultural appropriateness verified by native speaker
- [ ] RTL locales tested with actual Arabic/Hebrew text
- [ ] CJK fonts render correctly

### Current Translation Status

| Locale | Status | Reviewer |
|--------|--------|----------|
| en | Native | Core team |
| zh | Machine | Needs review |
| zh-Hant | Machine | Needs review |
| ko | Machine | Needs review |
| ja | Machine | Needs review |
| es | Machine | Needs review |
| pt | Machine | Needs review |
| ar | Machine | Needs review |
| hi | Machine | Needs review |
| fr | Machine | Needs review |
| de | Machine | Needs review |
| ru | Machine | Needs review |
| id | Machine | Needs review |
| vi | Machine | Needs review |
| th | Machine | Needs review |
