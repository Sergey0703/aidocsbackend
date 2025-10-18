// src/components/reports/ReportStatCard.jsx
import React from 'react';
import './ReportStatCard.css';

const ReportStatCard = ({ title, value, icon }) => {
  return (
    <div className="report-stat-card">
      <div className="card-icon">{icon}</div>
      <div className="card-content">
        <div className="card-title">{title}</div>
        <div className="card-value">{value}</div>
      </div>
    </div>
  );
};

export default ReportStatCard;