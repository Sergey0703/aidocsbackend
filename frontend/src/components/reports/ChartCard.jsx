// src/components/reports/ChartCard.jsx
import React from 'react';
import './ChartCard.css';

const ChartCard = ({ title, children }) => {
  return (
    <div className="chart-card">
      <div className="chart-card-header">
        <h3>{title}</h3>
      </div>
      <div className="chart-card-body">
        {children}
      </div>
    </div>
  );
};

export default ChartCard;