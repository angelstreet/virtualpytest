import ReactDOM from 'react-dom/client';

import App from './App.tsx';
import { CustomThemeProvider } from './contexts/ThemeContext';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <CustomThemeProvider>
    <App />
  </CustomThemeProvider>,
);
