import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input:
    './backend/openapi.json',
  output: {
    format: 'prettier',
    lint: 'eslint',
    path: './frontend/src/client',
  },
  plugins: [
    '@hey-api/client-axios',
    {
        name: 'zod',
        metadata: true,
        requests: true,
        responses: true,
        types: {
            infer: true,
        }
    },
    {
      enums: 'javascript',
      name: '@hey-api/typescript',
    },
    {
      name: '@hey-api/sdk',
      validator: 'zod',
    //   transformer: true,
    },
    // {
    //   dates: true,
    //   name: '@hey-api/transformers',
    // },
    // '@hey-api/schemas',
  ],
});
