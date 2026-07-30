// Original mark: a coin with a sly, "wise" expression (one relaxed eye,
// one raised eyebrow, a smirk) in front of two fanned cash bills. Not a
// depiction of either Pennywise the clown (Warner Bros./Stephen King) or
// Alfred Pennyworth (DC) - just wordplay on the name via money + "wise".
export function PennywiseIcon({ size = 24 }: { size?: number }) {
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} aria-hidden="true">
      <rect
        x="4"
        y="19"
        width="36"
        height="21"
        rx="3"
        fill="#16a34a"
        stroke="#14532d"
        strokeWidth="1.5"
        transform="rotate(-14 22 30)"
      />
      <rect
        x="24"
        y="21"
        width="36"
        height="21"
        rx="3"
        fill="#22c55e"
        stroke="#14532d"
        strokeWidth="1.5"
        transform="rotate(11 42 32)"
      />
      <circle cx="32" cy="33" r="19" fill="#f5c518" stroke="#8a6d1a" strokeWidth="2.5" />
      <circle cx="25" cy="31" r="2.2" fill="#5c4413" />
      <path d="M34.5 28.5 q3.5 -3 7 0" stroke="#5c4413" strokeWidth="2.2" fill="none" strokeLinecap="round" />
      <path d="M23 39 q9 6 17 -1" stroke="#5c4413" strokeWidth="2.4" fill="none" strokeLinecap="round" />
    </svg>
  )
}
