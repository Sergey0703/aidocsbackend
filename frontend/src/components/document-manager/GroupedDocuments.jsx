// src/components/document-manager/GroupedDocuments.jsx
import React, { useState } from 'react';
import './GroupedDocuments.css';
import { FiFileText, FiCheck, FiPlusCircle } from 'react-icons/fi';

const GroupedDocuments = ({ group, onLink, onCreateAndLink }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLinking, setIsLinking] = useState(false);

  const { vrn, documents, vehicleDetails } = group;
  const documentCount = documents?.length || 0;

  // Check if vehicle exists
  const vehicleExists = vehicleDetails !== null && vehicleDetails !== undefined;

  // Handle link action
  const handleLink = async () => {
    if (isLinking) return;
    
    setIsLinking(true);
    try {
      const documentIds = documents.map(doc => doc.id);
      await onLink(vrn, documentIds);
    } catch (error) {
      console.error('Link failed:', error);
    } finally {
      setIsLinking(false);
    }
  };

  // Handle create and link action
  const handleCreateAndLink = async () => {
    if (isLinking) return;
    
    setIsLinking(true);
    try {
      const documentIds = documents.map(doc => doc.id);
      
      // Get vehicle details from extracted data if available
      const firstDoc = documents[0];
      const extractedData = firstDoc?.extracted_data || {};
      
      const vehicleDetails = {
        make: extractedData.make || null,
        model: extractedData.model || null,
      };
      
      await onCreateAndLink(vrn, documentIds, vehicleDetails);
    } catch (error) {
      console.error('Create and link failed:', error);
    } finally {
      setIsLinking(false);
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

  // Get file name from path
  const getFileName = (path) => {
    if (!path) return 'Unknown';
    return path.split('/').pop() || path;
  };

  return (
    <div className="grouped-documents-card">
      <div className="grouped-header">
        <div className="grouped-vrn-section">
          <div className="vrn-badge">{vrn}</div>
          <div className="document-count-badge">
            {documentCount} doc{documentCount !== 1 ? 's' : ''}
          </div>
        </div>

        {vehicleExists && vehicleDetails && (
          <div className="vehicle-info">
            {vehicleDetails.make && (
              <span className="vehicle-make">{vehicleDetails.make}</span>
            )}
            {vehicleDetails.model && (
              <span className="vehicle-model">{vehicleDetails.model}</span>
            )}
          </div>
        )}
      </div>

      {/* Document List Toggle */}
      <button
        className="toggle-documents-button"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <FiFileText />
        <span>{isExpanded ? 'Hide' : 'Show'} Documents</span>
        <span className={`toggle-arrow ${isExpanded ? 'expanded' : ''}`}>▼</span>
      </button>

      {/* Expandable Document List */}
      {isExpanded && (
        <div className="documents-list">
          {documents.map((doc) => (
            <div key={doc.id} className="document-item">
              <div className="document-icon">
                <FiFileText />
              </div>
              <div className="document-details">
                <div className="document-name">
                  {doc.original_filename || 'Unknown'}
                </div>
                <div className="document-meta">
                  <span className="document-date">
                    {formatDate(doc.uploaded_at)}
                  </span>
                  {doc.extracted_data?.extraction_method && (
                    <span className="extraction-method">
                      {doc.extracted_data.extraction_method}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Action Buttons */}
      <div className="grouped-actions">
        {vehicleExists ? (
          // Vehicle exists - show "Link to Vehicle" button
          <button
            className="action-button primary"
            onClick={handleLink}
            disabled={isLinking}
          >
            {isLinking ? (
              <>
                <span className="button-spinner"></span>
                <span>Linking...</span>
              </>
            ) : (
              <>
                <FiCheck />
                <span>Link to Vehicle {vrn}</span>
              </>
            )}
          </button>
        ) : (
          // Vehicle doesn't exist - show "Create Vehicle + Link" button
          <button
            className="action-button create"
            onClick={handleCreateAndLink}
            disabled={isLinking}
          >
            {isLinking ? (
              <>
                <span className="button-spinner"></span>
                <span>Creating...</span>
              </>
            ) : (
              <>
                <FiPlusCircle />
                <span>Create Vehicle + Link</span>
              </>
            )}
          </button>
        )}
      </div>

      {/* Status Footer */}
      <div className="grouped-footer">
        {vehicleExists ? (
          <p className="status-text success">
            ✅ Vehicle found in system
          </p>
        ) : (
          <p className="status-text warning">
            ⚠️ Vehicle not found - will be created
          </p>
        )}
      </div>
    </div>
  );
};

export default GroupedDocuments;