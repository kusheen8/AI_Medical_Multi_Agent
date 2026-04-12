import React from 'react';
import './App.css';
import { AppProvider } from './context/AppContext';
import MainLayout from './components/Layout/MainLayout';

function App() {
  return (
    <AppProvider>
      <MainLayout />
    </AppProvider>
  );
}

export default App;
