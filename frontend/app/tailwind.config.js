/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#e6edf3",
        "muted-ink": "#8b98a5",
        panel: "#12161c",
        "panel-light": "#161b22",
        line: "#232a34",
        "line-strong": "#2d3542",
        teal: "#2dd4bf",
        amber: "#f5a623",
        red: "#f0554a",
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
