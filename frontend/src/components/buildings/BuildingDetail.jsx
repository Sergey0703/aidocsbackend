// src/components/buildings/BuildingDetail.jsx
import React, { useState } from 'react';
import './BuildingDetail.css';
import { FiFileText, FiAlertCircle } from 'react-icons/fi';

const BuildingDetail = ({ building }) => {
  const [activeTab, setActiveTab] = useState('documents');

  if (!building) return null;

  return (
    <div className="detail-container">
      {/* Header */}
      <header className="detail-header">
        <div className="detail-title">
          <h2>{building.name}</h2>
          <p>{building.address}</p>
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
          Documents ({building.documents?.length || 0})
        </button>
      </div>

      {/* Body */}
      <div className="detail-body">
        {/* Details Tab */}
        {activeTab === 'details' && (
          <div className="details-tab-content">
            <div className="info-section">
              <h3>Building Information</h3>
              <div className="info-grid">
                <div className="info-item">
                  <label>Property Name</label>
                  <span>{building.name}</span>
                </div>
                <div className="info-item">
                  <label>Address</label>
                  <span>{building.address}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Documents Tab */}
        {activeTab === 'documents' && (
          <div className="documents-tab-content">
            {building.documents && building.documents.length > 0 ? (
              <div className="doc-list-detail">
                {building.documents.map(doc => (
                  <div key={doc.id} className="doc-item-detail">
                    <div className="doc-info">
                      <div className="doc-name">
                        <FiFileText />
                        <span>{doc.title}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="no-documents">
                <FiAlertCircle className="no-docs-icon" />
                <h3>No Documents Found</h3>
                <p>This property has no linked documents yet.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default BuildingDetail;