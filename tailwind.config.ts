import type { Config } from "tailwindcss";

// Analyse les composants de l'application et définit la palette de l'église.
const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        epm: {
          navy: "#153b70",
          blue: "#1769aa",
          red: "#cf4148",
          paper: "#f5f8fc",
        },
      },
    },
  },
  plugins: [],
};

export default config;
