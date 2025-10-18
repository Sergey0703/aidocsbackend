// src/layouts/MainLayout.jsx
import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/common/Sidebar'; // Мы создадим этот компонент позже
import Header from '../components/layout/Header';   // И этот тоже
import './MainLayout.css';

const MainLayout = () => {
  return (
    <div className="main-layout">
      <Sidebar />
      <div className="content-wrapper">
        {/* <Header /> */}
        <main className="page-content">
          <Outlet /> {/* Здесь будут отображаться дочерние страницы */}
        </main>
      </div>
    </div>
  );
};

export default MainLayout;