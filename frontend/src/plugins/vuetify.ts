/**
 * plugins/vuetify.ts
 *
 * Framework documentation: https://vuetifyjs.com`
 */

// Styles
import '@mdi/font/css/materialdesignicons.css';
import 'vuetify/styles';

// Composables
import { createVuetify } from 'vuetify';

// https://vuetifyjs.com/en/introduction/why-vuetify/#feature-guides
export default createVuetify({
  theme: {
    defaultTheme: 'startupLight',

    themes: {
      startupLight: {
        dark: false,
        colors: {
          primary: '#2c6fff',
          secondary: '#10b7c8',
          surface: '#ffffff',
          background: '#f4f8ff',
          success: '#14b86a',
          warning: '#f59e0b',
          error: '#ef4444',
          info: '#2563eb',
        },
      },
    },
  },
});
