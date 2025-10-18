// src/components/indexing/DocumentCard.jsx
import React, { useState } from 'react';
import './DocumentCard.css';

const DocumentCard = ({ document, onDelete }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatFileSize = (characters) => {
    if (!characters) return '0 KB';
    const bytes = characters; // Rough estimate
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    const mb = kb / 1024;
    return `${mb.toFixed(2)} MB`;
  };

  const getFileIcon = (fileType) => {
    switch (fileType?.toLowerCase()) {
      case 'pdf': return '📕';
      case 'docx':
      case 'doc': return '📘';
      case 'pptx':
      case 'ppt': return '📙';
      case 'txt': return '📄';
      case 'md': return '📝';
      default: return '📄';
    }
  };

  const getChunksBadgeColor = (chunks) => {
    if (chunks >= 100) return 'high';
    if (chunks >= 50) return 'medium';
    return 'low';
  };

  const handleDelete = async () => {
    if (isDeleting) return;

    setIsDeleting(true);
    try {
      await onDelete(document.filename);
    } catch (error) {
      console.error('Failed to delete:', error);
      setIsDeleting(false);
    }
  };

  return (
    <div className={`document-card ${isExpanded ? 'expanded' : ''}`}>
      {/* Card Header */}
      <div
        className="card-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="card-title">
          <span className="file-icon">{getFileIcon(document.file_type)}</span>
          <span className="filename" title={document.filename}>
            {document.filename}
          </span>
        </div>

        <div className="card-badges">
          <span className={`chunks-badge ${getChunksBadgeColor(document.total_chunks)}`}>
            {document.total_chunks} chunks
          </span>
          <button className="expand-button">
            {isExpanded ? '▼' : '▶'}
          </button>
        </div>
      </div>

      {/* Card Content (Expanded) */}
      {isExpanded && (
        <div className="card-content">
          <div className="document-details">
            <div className="detail-row">
              <span className="detail-label">📊 Total Chunks:</span>
              <span className="detail-value">{document.total_chunks}</span>
            </div>

            <div className="detail-row">
              <span className="detail-label">📏 Total Characters:</span>
              <span className="detail-value">
                {document.total_characters?.toLocaleString() || 0}
              </span>
            </div>

            <div className="detail-row">
              <span className="detail-label">📦 File Size:</span>
              <span className="detail-value">
                {formatFileSize(document.total_characters)}
              </span>
            </div>

            <div className="detail-row">
              <span className="detail-label">📝 File Type:</span>
              <span className="detail-value">
                {document.file_type?.toUpperCase() || 'Unknown'}
              </span>
            </div>

            <div className="detail-row">
              <span className="detail-label">📅 Indexed At:</span>
              <span className="detail-value">
                {formatDate(document.indexed_at)}
              </span>
            </div>
          </div>

          {/* Actions */}
          <div className="card-actions">
            <button
              className="delete-button"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              {isDeleting ? (
                <>
                  <span className="spinner-small"></span>
                  Deleting...
                </>
              ) : (
                <>
                  🗑️ Delete Document
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentCard;