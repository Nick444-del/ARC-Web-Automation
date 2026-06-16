
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { ArcApp } from './ArcApp';
import { VTransApp } from './VTransApp';
import { HmcApp } from './HmcApp';

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-gray-50 overflow-hidden font-sans">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<ArcApp />} />
            <Route path="/vtrans" element={<VTransApp />} />
            <Route path="/hmc" element={<HmcApp />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
