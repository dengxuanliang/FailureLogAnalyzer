const tsPlugin = require("@typescript-eslint/eslint-plugin");
const tsParser = require("@typescript-eslint/parser");
const reactPlugin = require("eslint-plugin-react");
const reactHooksPlugin = require("eslint-plugin-react-hooks");

module.exports = [
  {
    files: [
      "src/**/*.{ts,tsx,js,jsx}",
      "vite.config.ts",
      "jest.config.ts",
      "setupTests.ts",
    ],
    plugins: {
      "@typescript-eslint": tsPlugin,
      react: reactPlugin,
      "react-hooks": reactHooksPlugin,
    },
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        React: "readonly",
        process: "readonly",
        NodeJS: "readonly",
        document: "readonly",
        window: "readonly",
        atob: "readonly",
        btoa: "readonly",
        URLSearchParams: "readonly",
        HTMLFormElement: "readonly",
        __dirname: "readonly",
        test: "readonly",
        expect: "readonly",
        describe: "readonly",
        beforeAll: "readonly",
        beforeEach: "readonly",
        afterAll: "readonly",
        afterEach: "readonly",
        ImportMetaEnv: "readonly",
        it: "readonly",
        jest: "readonly",
        localStorage: "readonly",
      },
    },
    rules: {
      "react/react-in-jsx-scope": "off",
      "@typescript-eslint/strict-boolean-expressions": "off",
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "no-undef": "error",
    },
    settings: {
      react: {
        version: "detect",
      },
    },
  },
];
