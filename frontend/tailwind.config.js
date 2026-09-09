/** @type {import('tailwindcss').Config} */ export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["Arial", "sans-serif"] },
      colors: {
        ink: "#132a36",
        brand: {
          50: "#eef9f8",
          100: "#d8f1ee",
          500: "#168d86",
          600: "#0d746f",
          700: "#0b5c59",
        },
        blood: "#b33752",
      },
    },
  },
  plugins: [],
};
