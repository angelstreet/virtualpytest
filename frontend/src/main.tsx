import ReactDOM from 'react-dom/client';

import App from './App.tsx';
import { CustomThemeProvider } from './contexts/ThemeContext';
import './index.css';

// Auto-reload on chunk loading failure (fixes deployment 404s)
window.addEventListener('error', (event) => {
  if (event.message?.includes('Failed to fetch dynamically imported module')) {
    const hasReloaded = sessionStorage.getItem('chunk-load-reload');
    if (!hasReloaded) {
      sessionStorage.setItem('chunk-load-reload', 'true');
      window.location.reload();
    }
  }
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <CustomThemeProvider>
    <App />
  </CustomThemeProvider>,
);
