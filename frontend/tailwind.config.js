/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        company: {
          blue: '#1e3a8a', // Dark blue based on typical corporate logos
          light: '#eff6ff',
          accent: '#3b82f6'
        }
      }
    },
  },
  plugins: [],
}
