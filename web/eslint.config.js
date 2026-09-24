import js from '@eslint/js';
import ts from 'typescript-eslint';
import vue from 'eslint-plugin-vue';
import globals from 'globals';

export default ts.config(
  { ignores: ['node_modules/**', 'dist/**', 'storybook-static/**', 'playwright-report/**', 'test-results/**'] },
  js.configs.recommended,
  ...ts.configs.recommended,
  ...vue.configs['flat/essential'],
  {
    files: ['**/*.{js,mjs,ts,vue}'],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
    rules: {
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrors: 'none' }],
      // UI component filenames are existing public imports; naming changes add no safety.
      'vue/multi-word-component-names': 'off',
      '@typescript-eslint/no-unused-expressions': ['error', { allowShortCircuit: true, allowTernary: true }],
    },
  },
  { files: ['**/*.vue'], rules: { 'no-undef': 'off' }, languageOptions: { parserOptions: { parser: ts.parser, extraFileExtensions: ['.vue'] } } },
  {
    files: ['tests/**/*.{js,ts}'],
    // Tests intentionally use broad fixture doubles and Playwright's empty fixture
    // destructuring. Keep real hygiene rules (unused symbols, undefined names, etc.)
    // while allowing these test-specific patterns.
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
      'no-empty-pattern': 'off',
    },
  },
  {
    files: ['src/runtime/runtime.js'],
    // SA-10: the JS bridge intentionally exposes callbacks and legacy helpers;
    // retain correctness rules while tracking unused-symbol cleanup separately.
    rules: { '@typescript-eslint/no-unused-vars': 'off' },
  },
);
