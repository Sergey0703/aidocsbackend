// src/App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import SearchPage from './pages/SearchPage';
import IndexingPage from './pages/IndexingPage';
import DocumentManagerPage from './pages/DocumentManagerPage';
import VehiclesPage from './pages/VehiclesPage';
// <-- ИМПОРТ НОВЫХ СТРАНИЦ -->
import BuildingsPage from './pages/BuildingsPage';
import ReportsPage from './pages/ReportsPage';
import SettingsPage from './pages/SettingsPage';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<SearchPage />} />
          <Route path="indexing" element={<IndexingPage />} />
          <Route path="manager" element={<DocumentManagerPage />} />
          <Route path="vehicles" element={<VehiclesPage />} />
          {/* <-- НОВЫЕ МАРШРУТЫ --> */}
          <Route path="buildings" element={<BuildingsPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;