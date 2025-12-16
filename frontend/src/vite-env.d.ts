/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_VERSION: string;
  readonly VITE_API_URL: string;
  readonly VITE_HOST: string;
  readonly VITE_DEFAULT_LANG: string;
  readonly VITE_LOCALE: string;
  readonly VITE_CURRENCY: string;
  readonly VITE_MORE_INFO_OCP_URL: string;
  readonly VITE_MAX_FILE_SIZE_MB: number;
  // more env variables...
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// declare module '*.svg' {
//   const content: React.FC<React.SVGProps<SVGElement>>;
//   export default content;
// }
