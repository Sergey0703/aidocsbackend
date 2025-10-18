// src/components/vehicles/VehicleDetail.jsx
import React, { useState } from 'react';
import './VehicleDetail.css';
import { FiFileText, FiEdit, FiTrash2, FiAlertCircle } from 'react-icons/fi';

const VehicleDetail = ({ vehicle, onDelete, onUnlinkDocument, onEdit }) => {
  const [activeTab, setActiveTab] = useState('details');
  const [unlinkingDocId, setUnlinkingDocId] = useState(null);

  if (!vehicle) return null;

  // ========================================================================
  // HELPER FUNCTIONS
  // ========================================================================

  // Format date helper
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch (e) {
      return 'Invalid date';
    }
  };

  // Calculate days until expiry
  const getDaysUntilExpiry = (dateString) => {
    if (!dateString) return null;
    
    try {
      const expiryDate = new Date(dateString);
      const today = new Date();
      const diffTime = expiryDate - today;
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      return diffDays;
    } catch (e) {
      return null;
    }
  };

  // Get expiry badge with color
  const getExpiryBadge = (days) => {
    if (days === null) return null;
    
    if (days < 0) {
      return <span className="expiry-badge expired">❌ Expired {Math.abs(days)} days ago</span>;
    } else if (days === 0) {
      return <span className="expiry-badge expires-today">⚠️ Expires today</span>;
    } else if (days <= 30) {
      return <span className="expiry-badge expires-soon">⚠️ Expires in {days} days</span>;
    } else {
      return <span className="expiry-badge expires-later">✅ {days} days remaining</span>;
    }
  };

  // Get status badge
  const getStatusBadge = (status) => {
    const statusMap = {
      active: { class: 'status-active', label: '✅ Active' },
      maintenance: { class: 'status-maintenance', label: '🔧 Maintenance' },
      inactive: { class: 'status-inactive', label: '⏸️ Inactive' },
      sold: { class: 'status-sold', label: '💰 Sold' },
      archived: { class: 'status-archived', label: '📦 Archived' },
    };

    const statusInfo = statusMap[status?.toLowerCase()] || { class: '', label: status };
    
    return <span className={`status-badge ${statusInfo.class}`}>{statusInfo.label}</span>;
  };

  // Handle unlink with loading state
  const handleUnlink = async (documentId) => {
    setUnlinkingDocId(documentId);
    try {
      await onUnlinkDocument(documentId);
    } finally {
      setUnlinkingDocId(null);
    }
  };

  // Get document filename from path
  const getDocumentFilename = (doc) => {
    if (doc.filename) return doc.filename;
    if (doc.raw_file_path) return doc.raw_file_path.split('/').pop();
    if (doc.markdown_file_path) return doc.markdown_file_path.split('/').pop();
    return 'Unknown Document';
  };

  // Get document status badge
  const getDocumentStatusBadge = (status) => {
    const statusMap = {
      unassigned: { class: 'doc-status-unassigned', icon: '⏸️', label: 'Unassigned' },
      assigned: { class: 'doc-status-assigned', icon: '📎', label: 'Assigned' },
      pending_ocr: { class: 'doc-status-pending', icon: '🔄', label: 'OCR Pending' },
      pending_indexing: { class: 'doc-status-pending', icon: '⏳', label: 'Indexing' },
      processed: { class: 'doc-status-processed', icon: '✅', label: 'Processed' },
      failed: { class: 'doc-status-failed', icon: '❌', label: 'Failed' },
      archived: { class: 'doc-status-archived', icon: '📦', label: 'Archived' },
    };

    const statusInfo = statusMap[status?.toLowerCase()] || { class: '', icon: '❓', label: status };
    
    return (
      <span className={`doc-status-badge ${statusInfo.class}`}>
        {statusInfo.icon} {statusInfo.label}
      </span>
    );
  };

  // ========================================================================
  // RENDER
  // ========================================================================

  return (
    <div className="detail-container">
      {/* Header */}
      <header className="detail-header">
        <div className="detail-title">
          <h2>{vehicle.registration_number}</h2>
          <p>{vehicle.make} {vehicle.model}</p>
        </div>
        <div className="header-actions">
          {onEdit && (
            <button 
  className="edit-btn" 
  onClick={() => onEdit ? onEdit(vehicle) : console.log('No onEdit handler')}
>
  <FiEdit /> Edit
</button>
          )}
          <button className="delete-btn" onClick={() => onDelete(vehicle)}>
            <FiTrash2 /> Delete
          </button>
        </div>
      </header>

      {/* Tabs */}
      <div className="detail-tabs">
        <button 
          className={`tab-btn ${activeTab === 'details' ? 'active' : ''}`} 
          onClick={() => setActiveTab('details')}
        >
          Details
        </button>
        <button 
          className={`tab-btn ${activeTab === 'documents' ? 'active' : ''}`} 
          onClick={() => setActiveTab('documents')}
        >
          Documents ({vehicle.documents?.length || 0})
        </button>
      </div>

      {/* Body */}
      <div className="detail-body">
        {/* Details Tab */}
        {activeTab === 'details' && (
          <div className="details-tab-content">
            {/* Basic Info Section */}
            <div className="info-section">
              <h3>Basic Information</h3>
              <div className="info-grid">
                <div className="info-item">
                  <label>VIN Number</label>
                  <span>{vehicle.vin_number || 'N/A'}</span>
                </div>
                <div className="info-item">
                  <label>Status</label>
                  {getStatusBadge(vehicle.status)}
                </div>
                <div className="info-item">
                  <label>Make</label>
                  <span>{vehicle.make || 'N/A'}</span>
                </div>
                <div className="info-item">
                  <label>Model</label>
                  <span>{vehicle.model || 'N/A'}</span>
                </div>
                <div className="info-item">
                  <label>Current Driver</label>
                  <span>{vehicle.current_driver_id || 'Unassigned'}</span>
                </div>
              </div>
            </div>

            {/* Expiry Dates Section */}
            <div className="info-section">
              <h3>Expiry Dates</h3>
              
              {/* Insurance */}
              <div className="expiry-item">
                <div className="expiry-header">
                  <label>Insurance Expiry</label>
                  <span className="expiry-date">{formatDate(vehicle.insurance_expiry_date)}</span>
                </div>
                {getExpiryBadge(getDaysUntilExpiry(vehicle.insurance_expiry_date))}
              </div>

              {/* Motor Tax */}
              <div className="expiry-item">
                <div className="expiry-header">
                  <label>Motor Tax Expiry</label>
                  <span className="expiry-date">{formatDate(vehicle.motor_tax_expiry_date)}</span>
                </div>
                {getExpiryBadge(getDaysUntilExpiry(vehicle.motor_tax_expiry_date))}
              </div>

              {/* NCT */}
              <div className="expiry-item">
                <div className="expiry-header">
                  <label>NCT Expiry</label>
                  <span className="expiry-date">{formatDate(vehicle.nct_expiry_date)}</span>
                </div>
                {getExpiryBadge(getDaysUntilExpiry(vehicle.nct_expiry_date))}
              </div>
            </div>

            {/* Metadata Section */}
            <div className="info-section">
              <h3>Metadata</h3>
              <div className="info-grid">
                <div className="info-item">
                  <label>Created At</label>
                  <span>{formatDate(vehicle.created_at)}</span>
                </div>
                <div className="info-item">
                  <label>Updated At</label>
                  <span>{formatDate(vehicle.updated_at)}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Documents Tab */}
        {activeTab === 'documents' && (
          <div className="documents-tab-content">
            {vehicle.documents && vehicle.documents.length > 0 ? (
              <div className="doc-list-detail">
                {vehicle.documents.map(doc => (
                  <div key={doc.id} className="doc-item-detail">
                    <div className="doc-info">
                      <div className="doc-name">
                        <FiFileText />
                        <span>{getDocumentFilename(doc)}</span>
                      </div>
                      <div className="doc-meta">
                        {getDocumentStatusBadge(doc.status)}
                        {doc.document_type && (
                          <span className="doc-type-badge">{doc.document_type}</span>
                        )}
                      </div>
                    </div>
                    <button 
                      className="unlink-btn" 
                      onClick={() => handleUnlink(doc.id)}
                      disabled={unlinkingDocId === doc.id}
                    >
                      {unlinkingDocId === doc.id ? '⏳ Unlinking...' : 'Unlink'}
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="no-documents">
                <FiAlertCircle className="no-docs-icon" />
                <h3>No Documents Linked</h3>
                <p>This vehicle has no linked documents yet.</p>
                <p className="hint">Go to Document Manager to link documents to this vehicle.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default VehicleDetail;