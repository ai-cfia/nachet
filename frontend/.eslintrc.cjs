// .eslintrc.cjs
module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    jest: true,
  },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
    "plugin:react/recommended",
    "plugin:import/typescript",
    "plugin:prettier/recommended",
  ],
  parserOptions: {
    ecmaFeatures: {
      jsx: true,
    },
    ecmaVersion: 12,
    sourceType: "module",
    project: "./tsconfig.json",
  },
  plugins: [
    "react",
    "@typescript-eslint",
    "react-hooks",
    "prettier",
    "react-refresh",
  ],
  overrides: [
    {
      files: ["__mocks__/**/*.js"],
      rules: {
        "no-undef": "off", // Turn off the 'no-undef' rule
      },
      env: {
        commonjs: true, // Set environment to CommonJS
      },
    },
  ],
  rules: {
    "react/prop-types": "off",
    "react/react-in-jsx-scope": "off", // React 17+ doesn't require React to be in scope when using JSX
    "prettier/prettier": ["error", { endOfLine: "auto" }],
    "react-refresh/only-export-components": [
      "warn",
      { allowConstantExport: true },
    ],
    "@typescript-eslint/no-explicit-any": "off",
    // Add any other custom rules or overrides here
  },
  settings: {
    react: {
      version: "detect", // Automatically detect the React version
    },
  },
  ignorePatterns: [
    "dist",
    "node_modules",
    "jest.config.cjs",
    ".eslintrc.cjs",
    "__mocks__",
    "vitest.config.ts",
  ],
};
