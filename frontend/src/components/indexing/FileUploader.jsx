// src/components/indexing/FileUploader.jsx
import React, { useState, useRef } from 'react';
import './FileUploader.css';

const FileUploader = ({ onFilesSelected, disabled, settings, onSettingsChange }) => {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const MAX_FILES = 5;

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (disabled) return;

    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  };

  const handleFileInput = (e) => {
    const files = Array.from(e.target.files);
    handleFiles(files);
  };

  const handleFiles = (files) => {
    if (files.length > MAX_FILES) {
      alert(`Maximum ${MAX_FILES} files allowed. Selected ${files.length} files.`);
      return;
    }

    // Filter for supported formats (you can expand this)
    const supportedFormats = ['.pdf', '.docx', '.doc', '.pptx', '.ppt', '.txt', '.html', '.htm', '.md', '.png', '.jpg', '.jpeg'];
    const validFiles = files.filter(file => {
      const ext = '.' + file.name.split('.').pop().toLowerCase();
      return supportedFormats.includes(ext);
    });

    if (validFiles.length !== files.length) {
      alert(`Some files were filtered out. Only supported formats: ${supportedFormats.join(', ')}`);
    }

    setSelectedFiles(validFiles);
  };

  const handleUpload = () => {
    if (selectedFiles.length === 0) {
      alert('Please select files first');
      return;
    }

    onFilesSelected(selectedFiles);
    setSelectedFiles([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleRemoveFile = (index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleClear = () => {
    setSelectedFiles([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="file-uploader">
      {/* Drag & Drop Zone */}
      <div
        className={`drop-zone ${dragActive ? 'active' : ''} ${disabled ? 'disabled' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <div className="drop-zone-content">
          <div className="upload-icon">📁</div>
          <p className="drop-zone-title">
            {dragActive ? 'Drop files here' : 'Drag & drop files here'}
          </p>
          <p className="drop-zone-subtitle">or</p>
          <button
            className="choose-files-button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
          >
            Choose Files
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileInput}
            style={{ display: 'none' }}
            accept=".pdf,.docx,.doc,.pptx,.ppt,.txt,.html,.htm,.md,.png,.jpg,.jpeg"
            disabled={disabled}
          />
          <p className="file-limit">Maximum {MAX_FILES} files</p>
        </div>
      </div>

      {/* Selected Files List */}
      {selectedFiles.length > 0 && (
        <div className="selected-files">
          <div className="selected-files-header">
            <h4>Selected Files ({selectedFiles.length}/{MAX_FILES})</h4>
            <button className="clear-button" onClick={handleClear}>
              Clear All
            </button>
          </div>
          <ul className="files-list">
            {selectedFiles.map((file, index) => (
              <li key={index} className="file-item">
                <div className="file-info">
                  <span className="file-icon">📄</span>
                  <div className="file-details">
                    <span className="file-name">{file.name}</span>
                    <span className="file-size">{formatFileSize(file.size)}</span>
                  </div>
                </div>
                <button
                  className="remove-button"
                  onClick={() => handleRemoveFile(index)}
                  title="Remove file"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Settings */}
      <div className="upload-settings">
        <h4>Conversion Settings</h4>
        <div className="settings-list">
          <label className="setting-checkbox">
            <input
              type="checkbox"
              checked={settings.incremental}
              onChange={(e) => onSettingsChange({
                ...settings,
                incremental: e.target.checked
              })}
              disabled={disabled}
            />
            <span>Incremental (skip already converted)</span>
          </label>

          <label className="setting-checkbox">
            <input
              type="checkbox"
              checked={settings.enableOcr}
              onChange={(e) => onSettingsChange({
                ...settings,
                enableOcr: e.target.checked
              })}
              disabled={disabled}
            />
            <span>Enable OCR (for images and scanned PDFs)</span>
          </label>

          <div className="setting-input">
            <label>Max file size (MB):</label>
            <input
              type="number"
              min="1"
              max="500"
              value={settings.maxFileSizeMb}
              onChange={(e) => onSettingsChange({
                ...settings,
                maxFileSizeMb: parseInt(e.target.value)
              })}
              disabled={disabled}
            />
          </div>
        </div>
      </div>

      {/* Upload Button */}
      {selectedFiles.length > 0 && (
        <button
          className="upload-button"
          onClick={handleUpload}
          disabled={disabled}
        >
          Start Conversion ({selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''})
        </button>
      )}
    </div>
  );
};

export default FileUploader;