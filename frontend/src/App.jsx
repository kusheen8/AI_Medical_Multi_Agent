import React, { useContext } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import { AppProvider, AppContext } from './context/AppContext';
import MainLayout from './components/Layout/MainLayout';
import Login from './components/Views/Login';

function AuthGate({ children }) {
  const { isAuthenticated } = useContext(AppContext);
  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

function AppRoutes() {
  const { isAuthenticated } = useContext(AppContext);
  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/*" element={
        <AuthGate>
          <MainLayout />
        </AuthGate>
      } />
    </Routes>
  );
}

function App() {
  return (
    <AppProvider>
      <AppRoutes />
    </AppProvider>
  );
}

export default App;
