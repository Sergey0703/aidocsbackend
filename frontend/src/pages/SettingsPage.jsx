// src/pages/SettingsPage.jsx
import React, { useState } from 'react';
import './SettingsPage.css';
import SettingsCard from '../components/settings/SettingsCard';
import SettingsControl from '../components/settings/SettingsControl';

const SettingsPage = () => {
  const [settings, setSettings] = useState({
    languageModel: 'gpt-4-turbo',
    ocrMode: 'high-accuracy',
    batchSize: 50,
    emailNotifications: true,
    retentionDays: 365,
    theme: 'light',
  });

  const handleSettingChange = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="settings-page">
      <header className="settings-header">
        <h1>System Settings</h1>
        <p>Manage system-wide configuration for document processing and user interface.</p>
      </header>

      <SettingsCard
        title="AI & Processing"
        description="Configure the core AI models and document processing pipeline."
      >
        <SettingsControl
          label="Language Model"
          description="Select the primary model for text analysis and summarization."
        >
          <select
            value={settings.languageModel}
            onChange={(e) => handleSettingChange('languageModel', e.target.value)}
          >
            <option value="gpt-4-turbo">GPT-4 Turbo</option>
            <option value="claude-3-opus">Claude 3 Opus</option>
            <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
          </select>
        </SettingsControl>

        <SettingsControl
          label="OCR Processing Mode"
          description="Choose the OCR mode for image-to-text conversion."
        >
          <select
            value={settings.ocrMode}
            onChange={(e) => handleSettingChange('ocrMode', e.target.value)}
          >
            <option value="fast">Fast (Lower Accuracy)</option>
            <option value="balanced">Balanced</option>
            <option value="high-accuracy">High Accuracy (Slower)</option>
          </select>
        </SettingsControl>

        <SettingsControl
          label="Indexing Batch Size"
          description={`Process up to ${settings.batchSize} documents at a time.`}
        >
          <div className="slider-container">
            <input
              type="range"
              min="10"
              max="100"
              step="10"
              value={settings.batchSize}
              onChange={(e) => handleSettingChange('batchSize', parseInt(e.target.value))}
            />
            <span>{settings.batchSize}</span>
          </div>
        </SettingsControl>
      </SettingsCard>

      <SettingsCard
        title="General & User Interface"
        description="Manage general application settings and user preferences."
      >
        <SettingsControl
          label="Enable Email Notifications"
          description="Receive email alerts for important system events."
        >
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={settings.emailNotifications}
              onChange={(e) => handleSettingChange('emailNotifications', e.target.checked)}
            />
            <span className="slider"></span>
          </label>
        </SettingsControl>

        <SettingsControl
          label="Data Retention Policy (Days)"
          description="Automatically delete processed documents after this period."
        >
          <input
            type="number"
            value={settings.retentionDays}
            onChange={(e) => handleSettingChange('retentionDays', parseInt(e.target.value))}
          />
        </SettingsControl>

        <SettingsControl
          label="Appearance"
          description="Switch between light and dark mode."
        >
          <div className="theme-toggle">
            <button
              className={settings.theme === 'light' ? 'active' : ''}
              onClick={() => handleSettingChange('theme', 'light')}
            >
              Light
            </button>
            <button
              className={settings.theme === 'dark' ? 'active' : ''}
              onClick={() => handleSettingChange('theme', 'dark')}
            >
              Dark
            </button>
          </div>
        </SettingsControl>
      </SettingsCard>
    </div>
  );
};

export default SettingsPage;