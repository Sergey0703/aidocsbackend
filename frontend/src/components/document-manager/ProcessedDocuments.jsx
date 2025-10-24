// src/components/document-manager/ProcessedDocuments.jsx
import React, { useState } from 'react';
import './ProcessedDocuments.css';
import { FiFileText, FiCheckSquare, FiSquare } from 'react-icons/fi';

const ProcessedDocuments = ({ documents, onFindVRN, isProcessing }) => {
  const [selectedDocs, setSelectedDocs] = useState([]);
  const [selectAll, setSelectAll] = useState(false);

  // Toggle select all
  const handleSelectAll = () => {
    if (selectAll) {
      setSelectedDocs([]);
      setSelectAll(false);
    } else {
      setSelectedDocs(documents.map(doc => doc.id));
      setSelectAll(true);
    }
  };

  // Toggle individual document
  const handleToggleDoc = (docId) => {
    if (selectedDocs.includes(docId)) {
      setSelectedDocs(selectedDocs.filter(id => id !== docId));
      setSelectAll(false);
    } else {
      const newSelected = [...selectedDocs, docId];
      setSelectedDocs(newSelected);
      if (newSelected.length === documents.length) {
        setSelectAll(true);
      }
    }
  };

  // Handle find VRN click
  const handleFindVRN = () => {
    if (selectedDocs.length > 0) {
      // Find VRN in selected documents
      onFindVRN(selectedDocs);
    } else {
      // Find VRN in all documents
      onFindVRN(null);
    }
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IE', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  // Get file name from document (supports both Storage and filesystem modes)
  const getFileName = (doc) => {
    // Storage mode: use original_filename
    if (doc.original_filename) {
      return doc.original_filename;
    }
    // Filesystem mode: extract from raw_file_path
    if (doc.raw_file_path) {
      return doc.raw_file_path.split('/').pop() || doc.raw_file_path;
    }
    return 'Unknown';
  };

  if (documents.length === 0) {
    return (
      <div className="processed-documents-empty">
        <div className="empty-icon">📋</div>
        <h3>No Documents Need Analysis</h3>
        <p>All indexed documents have been analyzed for VRN.</p>
      </div>
    );
  }

  return (
    <div className="processed-documents">
      <div className="processed-header">
        <div className="processed-title">
          <h3>Documents Needing VRN Analysis</h3>
          <span className="document-count">{documents.length} document{documents.length !== 1 ? 's' : ''}</span>
        </div>
        
        <div className="processed-actions">
          <button
            className="select-all-button"
            onClick={handleSelectAll}
            disabled={isProcessing}
          >
            {selectAll ? <FiCheckSquare /> : <FiSquare />}
            <span>{selectAll ? 'Deselect All' : 'Select All'}</span>
          </button>
          
          <button
            className="find-vrn-action-button"
            onClick={handleFindVRN}
            disabled={isProcessing}
          >
            {isProcessing ? (
              <>
                <span className="spinner"></span>
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <span>Find VRN</span>
                {selectedDocs.length > 0 && (
                  <span className="selected-badge">{selectedDocs.length}</span>
                )}
              </>
            )}
          </button>
        </div>
      </div>

      <div className="processed-list">
        {documents.map((doc) => (
          <div
            key={doc.id}
            className={`processed-item ${selectedDocs.includes(doc.id) ? 'selected' : ''}`}
            onClick={() => !isProcessing && handleToggleDoc(doc.id)}
          >
            <div className="processed-checkbox">
              {selectedDocs.includes(doc.id) ? (
                <FiCheckSquare className="checkbox-icon checked" />
              ) : (
                <FiSquare className="checkbox-icon" />
              )}
            </div>

            <div className="processed-icon">
              <FiFileText />
            </div>

            <div className="processed-info">
              <div className="processed-filename">
                {getFileName(doc)}
              </div>
              <div className="processed-meta">
                <span className="processed-date">
                  Uploaded: {formatDate(doc.uploaded_at)}
                </span>
                <span className="processed-status-badge">
                  {doc.status || 'processed'}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="processed-footer">
        <p className="processed-hint">
          💡 Select specific documents or click "Find VRN" to analyze all {documents.length} document{documents.length !== 1 ? 's' : ''}
        </p>
      </div>
    </div>
  );
};

export default ProcessedDocuments;