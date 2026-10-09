import type { CSSProperties, ReactNode } from 'react'

/** 선 아이콘 모음 (24×24, 굵기·색은 .icon 클래스와 currentColor). 이모지 대신 써서 기기마다 같은 모양 */
const PATHS = {
  home: <path d="M4 10.5 12 4l8 6.5V19a1 1 0 0 1-1 1h-4.5v-5.5h-5V20H5a1 1 0 0 1-1-1z" />,
  receipt: (
    <>
      <path d="M6 3.5h12v17l-2-1.3-2 1.3-2-1.3-2 1.3-2-1.3-2 1.3z" />
      <path d="M9 8.5h6M9 12h6M9 15.5h3.5" />
    </>
  ),
  camera: (
    <>
      <path d="M4 8.5A1.5 1.5 0 0 1 5.5 7h2.3l1.5-2h5.4l1.5 2h2.3A1.5 1.5 0 0 1 20 8.5v9a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 17.5z" />
      <circle cx="12" cy="12.8" r="3.4" />
    </>
  ),
  wallet: (
    <>
      <path d="M17 9V6H5.5a1.5 1.5 0 0 0 0 3" />
      <path d="M4 7.5v10A1.5 1.5 0 0 0 5.5 19h13a1.5 1.5 0 0 0 1.5-1.5v-7A1.5 1.5 0 0 0 18.5 9h-13" />
      <path d="M16 14h.01" />
    </>
  ),
  sliders: (
    <>
      <path d="M4 7h9M17 7h3M4 17h3M11 17h9" />
      <circle cx="15" cy="7" r="2" />
      <circle cx="9" cy="17" r="2" />
    </>
  ),
  chevronDown: <path d="m6 9 6 6 6-6" />,
  chevronRight: <path d="m9 6 6 6-6 6" />,
  chevronLeft: <path d="m15 6-6 6 6 6" />,
  close: <path d="M6 6l12 12M18 6 6 18" />,
  check: <path d="m5 12.5 4.5 4.5L19 7.5" />,
  checkCircle: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="m8.5 12.2 2.4 2.4 4.6-4.8" />
    </>
  ),
  alert: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 8v4.5M12 16h.01" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 11v5M12 8h.01" />
    </>
  ),
  sparkle: (
    <>
      <path d="M12 4l1.6 4.4L18 10l-4.4 1.6L12 16l-1.6-4.4L6 10l4.4-1.6z" />
      <path d="M18.5 15.5l.6 1.4 1.4.6-1.4.6-.6 1.4-.6-1.4-1.4-.6 1.4-.6z" />
    </>
  ),
  image: (
    <>
      <rect x="4" y="5" width="16" height="14" rx="2" />
      <circle cx="9" cy="10" r="1.6" />
      <path d="m5 17 4.5-4.5 3 3 2.5-2.5L20 17" />
    </>
  ),
  copy: (
    <>
      <rect x="8" y="8" width="11" height="11" rx="2" />
      <path d="M16 8V6a1 1 0 0 0-1-1H6a1 1 0 0 0-1 1v9a1 1 0 0 0 1 1h2" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  trash: (
    <>
      <path d="M5 7h14M10 7V5h4v2M7 7l1 12h8l1-12" />
      <path d="M10.5 11v5M13.5 11v5" />
    </>
  ),
  zoom: (
    <>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4 4M11 8.5v5M8.5 11h5" />
    </>
  ),
  users: (
    <>
      <circle cx="9" cy="9" r="3.2" />
      <path d="M3.5 19a5.5 5.5 0 0 1 11 0" />
      <path d="M15.5 6.2a3 3 0 0 1 0 5.6M17.5 19a5.5 5.5 0 0 0-2.5-4.6" />
    </>
  ),
  logout: (
    <>
      <path d="M10 5H6a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h4" />
      <path d="M15 8l4 4-4 4M9 12h10" />
    </>
  ),
  swap: <path d="M7 7h12l-3-3M17 17H5l3 3" />,
  loader: <path d="M12 4a8 8 0 1 0 8 8" />,
  // 계정과목 아이콘 (lib/categoryStyle.ts 가 이름으로 고름)
  food: (
    <>
      <path d="M7 3.5V11M5 3.5v4a2 2 0 0 0 4 0v-4M7 11v9.5" />
      <path d="M16.5 20.5v-17c-2.2 1.3-3.5 3.8-3.5 6.8V13h3.5" />
    </>
  ),
  cup: (
    <>
      <path d="M6 8h11v5a5 5 0 0 1-5 5h-1a5 5 0 0 1-5-5z" />
      <path d="M17 9.5h1.5a2.5 2.5 0 0 1 0 5H17M9 3.5c-.6.9-.6 1.6 0 2.5M12.5 3.5c-.6.9-.6 1.6 0 2.5" />
    </>
  ),
  box: (
    <>
      <path d="M4 8 12 4l8 4v8.5l-8 4-8-4z" />
      <path d="m4 8 8 4 8-4M12 12v8.5" />
    </>
  ),
  print: (
    <>
      <path d="M7 9V4h10v5" />
      <rect x="4" y="9" width="16" height="7" rx="2" />
      <path d="M7 14h10v6H7z" />
    </>
  ),
  bus: (
    <>
      <rect x="5" y="3.5" width="14" height="14" rx="3" />
      <path d="M5 11h14M8.5 20.5v-3M15.5 20.5v-3M8.5 14.5h.01M15.5 14.5h.01" />
    </>
  ),
  party: (
    <>
      <path d="M4.5 19.5 8.7 8.2l7.1 7.1z" />
      <path d="M13.5 4.5c.6 1.6.2 2.9-.9 3.9M19.5 10.5c-1.6-.6-2.9-.2-3.9.9M17 4.5h.01M20 7.5h.01" />
    </>
  ),
  book: (
    <>
      <path d="M5 5.5A1.5 1.5 0 0 1 6.5 4H19v14H6.5A1.5 1.5 0 0 0 5 19.5z" />
      <path d="M5 19.5A1.5 1.5 0 0 0 6.5 21H19M9 8h6" />
    </>
  ),
  tag: (
    <>
      <path d="M4 12.5V5a1 1 0 0 1 1-1h7.5L20 11.5 12.5 19z" />
      <path d="M8.5 8.5h.01" />
    </>
  ),
  dots: <path d="M6.5 12h.01M12 12h.01M17.5 12h.01" style={{ strokeWidth: 3 }} />,
} satisfies Record<string, ReactNode>

export type IconName = keyof typeof PATHS

type Props = {
  name: IconName
  size?: number
  /** 선 굵기 (기본 1.8) */
  weight?: number
  className?: string
  style?: CSSProperties
}

export function Icon({ name, size = 24, weight, className, style }: Props) {
  return (
    <svg
      className={className ? `icon ${className}` : 'icon'}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
      style={weight ? { strokeWidth: weight, ...style } : style}
    >
      {PATHS[name]}
    </svg>
  )
}
