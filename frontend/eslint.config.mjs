import globals from "globals"
import js from "@eslint/js";
import typescriptParser from "@typescript-eslint/parser";
import typescriptPlugin from "@typescript-eslint/eslint-plugin";
import eslintReact from "@eslint-react/eslint-plugin";
import reactHooksPlugin from "eslint-plugin-react-hooks";
import reactRefreshPlugin from "eslint-plugin-react-refresh";
import prettierPlugin from "eslint-plugin-prettier";
import prettierConfig from "eslint-config-prettier";

export default [
  {
    ignores: [
      "**/dist",
      "**/node_modules",
      "**/jest.config.cjs",
      "**/.eslintrc.cjs",
      "**/__mocks__",
      "**/vitest.config.ts",
      "submodules",
      "src/client", // Exclude generated client code
    ],
  },
  js.configs.recommended,
  eslintReact.configs["recommended-typescript"],
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
        ...globals.jest,
        React: "readonly",
        global: "readonly",
      },
      ecmaVersion: 2022,
      sourceType: "module",
      parser: typescriptParser,
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
        project: "./tsconfig.json",
      },
    },
    plugins: {
      "@typescript-eslint": typescriptPlugin,
      "react-hooks": reactHooksPlugin,
      "react-refresh": reactRefreshPlugin.default ?? reactRefreshPlugin,
      prettier: prettierPlugin,
    },
    rules: {
      ...typescriptPlugin.configs.recommended.rules,
      ...eslintReact.configs["recommended-typescript"].rules,
      ...reactHooksPlugin.configs.recommended.rules,
      ...prettierConfig.rules,

      "react/prop-types": "off",
      "react/react-in-jsx-scope": "off",
      "@typescript-eslint/no-explicit-any": "off",

      "prettier/prettier": [
        "error",
        {
          endOfLine: "auto",
        },
      ],

      "react-refresh/only-export-components": [
        "warn",
        {
          allowConstantExport: true,
        },
      ],
    },
    settings: {
      react: {
        version: "detect",
      },
    },
  },
  {
    files: ["**/*.{js,cjs}"],
    languageOptions: {
      globals: {
        ...globals.node,
      },
      ecmaVersion: 2022,
      sourceType: "commonjs",
    },
  },
  {
    files: ["__mocks__/**/*.js"],
    rules: {
      "no-undef": "off",
    },
    languageOptions: {
      globals: {
        ...globals.commonjs,
      },
    },
  },
];
