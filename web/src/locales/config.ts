import i18n from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

import { LanguageAbbreviation } from '@/constants/common';
import translation_en from './en';
import { createTranslationTable, flattenObject } from './until';
import translation_zh from './zh';
import translation_zh_traditional from './zh-traditional';

const resources = {
  [LanguageAbbreviation.En]: translation_en,
  [LanguageAbbreviation.Zh]: translation_zh,
  [LanguageAbbreviation.ZhTraditional]: translation_zh_traditional,
};
const enFlattened = flattenObject(translation_en);

const zhFlattened = flattenObject(translation_zh);

const zh_traditionalFlattened = flattenObject(translation_zh_traditional);

export const translationTable = createTranslationTable(
  [enFlattened, zhFlattened, zh_traditionalFlattened],
  ['English', 'zh', 'zh-TRADITIONAL'],
);
i18n
  .use(initReactI18next)
  .use(LanguageDetector)
  .init({
    detection: {
      lookupLocalStorage: 'lng',
    },
    supportedLngs: Object.values(LanguageAbbreviation),
    resources,
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;
