/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    darkMode: 'class', // <--- THIS IS THE MAGIC LINE
    theme: {
        extend: {
            colors: {
                primary: "#2563EB",
                secondary: "#1E293B",
                accent: "#F59E0B",
                success: "#10B981",
                danger: "#EF4444",
            },
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
            },
        },
    },
    plugins: [],
}