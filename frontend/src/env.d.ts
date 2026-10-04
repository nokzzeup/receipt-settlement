/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 백엔드 주소. 비우면 같은 출처(/api)로 요청 → 개발 중엔 Vite 프록시가 백엔드로 넘김 */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
