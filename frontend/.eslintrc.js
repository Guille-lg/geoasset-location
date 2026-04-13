module.exports = {
  root: true,
  env: {
    node: true,
  },
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended',
    'plugin:@typescript-eslint/recommended',
    '@vue/eslint-config-typescript/recommended',
    'plugin:prettier/recommended', // This includes eslint-config-prettier and eslint-plugin-prettier
  ],
  rules: {
    'vue/multi-word-component-names': 'off',
    'vue/first-attribute-linebreak': 'off',
    'no-relative-import-paths/no-relative-import-paths': [
      'error',
      { allowSameFolder: false, prefix: '@', rootDir: 'src' },
    ],
  },
  plugins: ['@typescript-eslint', 'no-relative-import-paths'],
};
