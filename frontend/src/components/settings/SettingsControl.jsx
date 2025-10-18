// src/components/settings/SettingsControl.jsx
import React from 'react';
import './SettingsControl.css';

const SettingsControl = ({ label, description, children }) => {
  return (
    <div className="settings-control">
      <div className="control-label">
        <label>{label}</label>
        {description && <p>{description}</p>}
      </div>
      <div className="control-input">
        {children}
      </div>
    </div>
  );
};

export default SettingsControl;