/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'logic-blue': '#0ea5e9',
        'chaos-red': '#ef4444',
        'chaos-dark': '#7f1d1d',
        'dark-bg': '#0f172a',
        'board-bg': '#0f172a',
      }
    },
  },
  plugins: [],
}