/** @type {import('tailwindcss').Config} */
/*
 * Editorial light theme. Every token is explained, with contrast ratios, in
 * docs/DESIGN.md. Status colours are Tailwind's own rose / amber / emerald,
 * used through the exact class sets in components/RiskBadge.tsx.
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Paper and surfaces. Elevation is a border, never a shadow.
        canvas: "#FAF9F6", // the page: warm paper
        surface: "#FFFFFF", // panels, the agreement sheet
        sunken: "#F4F2EE", // table heads, wells, code
        hover: "#F5F3EF", // row hover and selection
        line: {
          DEFAULT: "#E7E4DD", // razor-thin dividers and panel borders
          strong: "#D5D1C7", // secondary buttons, dashed drop zone
          input: "#8E887F", // text-field boundary: 3:1 on white (WCAG 1.4.11)
        },
        // Ink.
        fg: {
          DEFAULT: "#1A1A1A",
          muted: "#57534E",
          faint: "#6F6A64",
        },
        // Brand: deep navy, built around #1E3A8A (navy-600).
        navy: {
          50: "#EFF3FB",
          100: "#DCE5F6",
          200: "#B9C8EC",
          300: "#8EA5DB",
          400: "#5B79C2",
          500: "#3355A6",
          600: "#1E3A8A",
          700: "#192F70",
          800: "#142558",
          900: "#0F1B40",
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        serif: ['"Newsreader"', "Georgia", "serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
      fontSize: {
        // Dense document scale. 2xs is for mono metadata only.
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
        xs: ["0.75rem", { lineHeight: "1.1rem" }],
        sm: ["0.8125rem", { lineHeight: "1.3rem" }],
        base: ["0.9375rem", { lineHeight: "1.55rem" }],
        lg: ["1.125rem", { lineHeight: "1.65rem" }],
        xl: ["1.375rem", { lineHeight: "1.85rem" }],
        "2xl": ["1.75rem", { lineHeight: "2.2rem" }],
        "3xl": ["2.25rem", { lineHeight: "2.6rem" }],
        "4xl": ["2.875rem", { lineHeight: "3.1rem" }],
      },
      boxShadow: {
        // Only for things that float above the page: menus, tooltips, status.
        float: "0 1px 2px rgba(26,26,26,0.04), 0 8px 24px -12px rgba(26,26,26,0.14)",
      },
      keyframes: {
        "seal-press": {
          "0%": { transform: "scale(1.22) rotate(-6deg)", opacity: "0" },
          "60%": { transform: "scale(0.98) rotate(-1.5deg)", opacity: "1" },
          "100%": { transform: "scale(1) rotate(-2deg)", opacity: "1" },
        },
        "marker-sweep": {
          "0%": { backgroundSize: "0% 100%" },
          "100%": { backgroundSize: "100% 100%" },
        },
        "link-draw": {
          "0%": { transform: "scaleY(0)" },
          "100%": { transform: "scaleY(1)" },
        },
        "row-in": {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        progress: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(350%)" },
        },
      },
      animation: {
        "seal-press": "seal-press 380ms cubic-bezier(.2,.8,.2,1) both",
        "marker-sweep": "marker-sweep 600ms cubic-bezier(.3,.7,.2,1) both",
        "link-draw": "link-draw 320ms ease-out both",
        "row-in": "row-in 260ms ease-out both",
        progress: "progress 1.3s cubic-bezier(.4,0,.2,1) infinite",
      },
    },
  },
  plugins: [],
};
