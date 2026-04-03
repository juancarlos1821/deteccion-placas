/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/**/*.js" 
  ],
  darkMode: 'class',
  theme: {
    extend: {
      // Agregamos esto para que la animación del sidebar sea profesional
      transitionProperty: {
        'width': 'width',
        'spacing': 'margin, padding',
      }
    },
  },
  plugins: [],
}