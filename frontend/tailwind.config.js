/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#182230",
        line: "#d9e1e8",
        brand: "#14532d",
        amberline: "#f59e0b",
      },
      boxShadow: {
        soft: "0 12px 32px rgba(24, 34, 48, 0.08)",
      },
    },
  },
  plugins: [],
};

