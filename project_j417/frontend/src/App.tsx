import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AppProvider } from '@/providers/AppProvider';
import Dashboard from '@/pages/Dashboard';

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
        </Routes>
      </BrowserRouter>
    </AppProvider>
  );
}
