const {
    defineConfig,
    globalIgnores,
} = require("eslint/config");

const globals = require("globals");

const {
    fixupConfigRules,
    fixupPluginRules,
} = require("@eslint/compat");

const react = require("eslint-plugin-react");
const typescriptEslint = require("@typescript-eslint/eslint-plugin");
const reactHooks = require("eslint-plugin-react-hooks");
const prettier = require("eslint-plugin-prettier");
const reactRefresh = require("eslint-plugin-react-refresh");
const js = require("@eslint/js");
const path = require("path");

const {
    FlatCompat,
} = require("@eslint/eslintrc");
const { default: path } = require("path");

const compat = new FlatCompat({
    baseDirectory: __dirname,
    recommendedConfig: js.configs.recommended,
    allConfig: js.configs.all
});

module.exports = defineConfig([{
    languageOptions: {
        globals: {
            ...globals.browser,
            ...globals.jest,
        },

        ecmaVersion: 12,
        sourceType: "module",

        parserOptions: {
            ecmaFeatures: {
                jsx: true,
            },

            // project: "./tsconfig.json",
            project: path.join(__dirname, "tsconfig.json"),
        },
    },

    extends: fixupConfigRules(compat.extends(
        "eslint:recommended",
        "plugin:@typescript-eslint/recommended",
        "plugin:react-hooks/recommended",
        "plugin:react/recommended",
        "plugin:import/typescript",
        "plugin:prettier/recommended",
    )),

    plugins: {
        react: fixupPluginRules(react),
        "@typescript-eslint": fixupPluginRules(typescriptEslint),
        "react-hooks": fixupPluginRules(reactHooks),
        prettier: fixupPluginRules(prettier),
        "react-refresh": reactRefresh,
    },

    rules: {
        "react/prop-types": "off",
        "react/react-in-jsx-scope": "off",

        "prettier/prettier": ["error", {
            endOfLine: "auto",
        }],

        "react-refresh/only-export-components": ["warn", {
            allowConstantExport: true,
        }],

        "@typescript-eslint/no-explicit-any": "off",
    },

    settings: {
        react: {
            version: "detect",
        },
    },
}, {
    files: ["__mocks__/**/*.js"],

    rules: {
        "no-undef": "off",
    },

    languageOptions: {
        globals: {
            ...globals.commonjs,
        },
    },
}, globalIgnores([
    "**/dist",
    "**/node_modules",
    "**/jest.config.cjs",
    "**/.eslintrc.cjs",
    "**/__mocks__",
    "**/vitest.config.ts",
])]);
