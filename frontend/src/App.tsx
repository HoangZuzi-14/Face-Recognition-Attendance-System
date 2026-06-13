import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider, useApp } from './context/AppContext';
import { AppShell } from './components/AppShell';

// Import Pages
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Classes } from './pages/Classes';
import { Enrollment } from './pages/Enrollment';
import { LiveAttendance } from './pages/LiveAttendance';
import { Events } from './pages/Events';
import { Reports } from './pages/Reports';
import { Settings } from './pages/Settings';

// Component kiểm tra và bảo vệ Route yêu cầu đăng nhập
const PrivateRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token } = useApp();
  const savedToken = localStorage.getItem('token');
  
  if (!token && !savedToken) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

// Component bảo vệ Route chỉ dành riêng cho Admin
const AdminRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useApp();
  const savedUser = localStorage.getItem('user');
  const activeUser = user || (savedUser ? JSON.parse(savedUser) : null);
  
  if (!activeUser || activeUser.role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }
  
  return <>{children}</>;
};

export const AppContent: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Route đăng nhập không bảo vệ */}
        <Route path="/login" element={<Login />} />

        {/* Các route nghiệp vụ bảo vệ qua AppShell và PrivateRoute */}
        <Route
          path="/"
          element={
            <PrivateRoute>
              <AppShell />
            </PrivateRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="classes" element={<Classes />} />
          <Route path="enrollment" element={<Enrollment />} />
          <Route path="live" element={<LiveAttendance />} />
          <Route path="events" element={<Events />} />
          <Route path="reports" element={<Reports />} />
          <Route path="settings" element={
            <AdminRoute>
              <Settings />
            </AdminRoute>
          } />
          
          {/* Fallback route */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}

export default App;
