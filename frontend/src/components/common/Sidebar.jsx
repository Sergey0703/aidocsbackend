// src/components/common/Sidebar.jsx
import React from 'react';
import { NavLink } from 'react-router-dom';
import './Sidebar.css';
import {
  FiSearch,
  FiUploadCloud,
  FiInbox,
  FiTruck,
  FiHome,
  FiBarChart2,
  FiSettings,
  FiUser
} from 'react-icons/fi';

const Sidebar = () => {
  const menuItems = [
    { to: "/", text: "Search", icon: <FiSearch /> },
    { to: "/indexing", text: "Indexing", icon: <FiUploadCloud /> },
    { to: "/manager", text: "Document Manager", icon: <FiInbox /> },
    { to: "/vehicles", text: "Vehicles", icon: <FiTruck /> }, // <-- ИКОНКА ИЗМЕНЕНА
    { to: "/buildings", text: "Buildings", icon: <FiHome /> },   // <-- НОВЫЙ ПУНКТ
    { to: "/reports", text: "Reports", icon: <FiBarChart2 /> }, // <-- НОВЫЙ ПУНКТ
    { to: "/settings", text: "Settings", icon: <FiSettings /> }, // <-- НОВЫЙ ПУНКТ
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2 className="sidebar-title">AI DOCS</h2>
      </div>
      <nav className="sidebar-nav">
        {menuItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
            end={item.to === "/"}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-text">{item.text}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">
        <div className="user-profile">
          <FiUser className="user-icon" />
          <span className="user-name">Mary</span>
        </div>
        <p className="version">v1.1.0</p>
      </div>
    </aside>
  );
};

export default Sidebar;