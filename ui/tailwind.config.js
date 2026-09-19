/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'dark-bg-1': '#0a0512',
        'dark-bg-2': '#1a0a2e',
        'accent-purple': '#a855f7',
        'accent-pink': '#ec4899',
        'accent-orange': '#f97316',
        'text-primary': '#f5f3ff',
        'text-muted': '#9ca3af',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Space Mono', 'Courier New', 'monospace'],
      },
    },
  },
  plugins: [],
}
