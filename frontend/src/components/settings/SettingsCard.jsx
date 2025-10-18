// src/components/settings/SettingsCard.jsx
import React from 'react';
import './SettingsCard.css';

const SettingsCard = ({ title, description, children }) => {
  return (
    <div className="settings-card">
      <div className="settings-card-header">
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      <div className="settings-card-body">
        {children}
      </div>
    </div>
  );
};

export default SettingsCard;