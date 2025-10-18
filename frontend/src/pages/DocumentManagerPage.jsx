// src/pages/DocumentManagerPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import './DocumentManagerPage.css';
import { ragApi } from '../api/ragApi';
import GroupedDocuments from '../components/document-manager/GroupedDocuments';
import UnassignedDocuments from '../components/document-manager/UnassignedDocuments';
import ProcessedDocuments from '../components/document-manager/ProcessedDocuments';
import FindVRNProgress from '../components/document-manager/FindVRNProgress';
import { FiSearch, FiRefreshCw } from 'react-icons/fi';

const DocumentManagerPage = () => {
  // Document states
  const [processedDocs, setProcessedDocs] = useState([]);
  const [groupedDocs, setGroupedDocs] = useState([]);
  const [unassignedDocs, setUnassignedDocs] = useState([]);
  
  // UI states
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // 🆕 VRN Finding states
  const [isFindingVRN, setIsFindingVRN] = useState(false);
  const [findVRNProgress, setFindVRNProgress] = useState(null);
  const [showProgress, setShowProgress] = useState(false);

  // Success notification state
  const [notification, setNotification] = useState(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      console.log('📡 Fetching documents for Document Manager...');
      const data = await ragApi.getUnassignedAndGroupedDocuments();
      console.log('✅ Documents loaded:', data);
      
      setProcessedDocs(data.processed || []);
      setGroupedDocs(data.grouped || []);
      setUnassignedDocs(data.unassigned || []);
    } catch (err) {
      console.error('❌ Failed to load documents:', err);
      setError("Failed to load documents. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Show notification
  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => {
      setNotification(null);
    }, 5000);
  };

  // 🆕 HANDLE FIND VRN
 const handleFindVRN = async (selectedDocIds = null) => {
  if (isFindingVRN) {
    console.warn('⚠️ VRN finding already in progress');
    return;
  }

  // Determine which documents to process
  const docsToProcess = selectedDocIds || processedDocs.map(d => d.id);
  const totalDocs = docsToProcess.length;

  if (totalDocs === 0) {
    alert('ℹ️ No documents to analyze.\n\nPlease upload and index documents first.');
    return;
  }

  // Show confirmation if there are many documents
  if (totalDocs > 20) {
    const confirmed = window.confirm(
      `You are about to analyze ${totalDocs} documents. This may take a few minutes. Continue?`
    );
    if (!confirmed) return;
  }

  setIsFindingVRN(true);
  setShowProgress(true);
  setFindVRNProgress({
    total: totalDocs,
    processed: 0,
    found: 0,
    notFound: 0,
    errors: 0,
    isRunning: true
  });

  try {
    console.log('🔍 Starting VRN extraction for', totalDocs, 'documents');

    // Call backend API
    const result = await ragApi.findVRNInDocuments(
      selectedDocIds ? selectedDocIds : null,
      true // use AI
    );

    console.log('✅ VRN extraction completed:', result);

    // Update progress with final results
    setFindVRNProgress({
      total: result.total_processed || totalDocs,
      processed: result.total_processed || 0,
      found: result.vrn_found || 0,
      notFound: result.vrn_not_found || 0,
      errors: result.failed || 0,
      isRunning: false
    });

    // Show notification
    if (result.vrn_found > 0) {
      showNotification(
        `Successfully extracted VRN from ${result.vrn_found} document(s)`,
        'success'
      );
    } else {
      showNotification(
        `No VRN found in ${result.total_processed} document(s)`,
        'info'
      );
    }

    // Refresh data immediately
    setTimeout(async () => {
      console.log('🔄 Refreshing data...');
      await fetchData();
      setShowProgress(false);
    }, 500);

  } catch (err) {
    console.error('❌ VRN extraction failed:', err);
    const errorMessage = err.response?.data?.detail || err.message || 'Unknown error';
    setError(`Failed to find VRN: ${errorMessage}`);
    
    setFindVRNProgress(prev => ({
      ...prev,
      isRunning: false,
      errors: (prev?.errors || 0) + 1
    }));

    showNotification(
      `VRN extraction failed: ${errorMessage}`,
      'error'
    );

    // Hide progress after error
    setTimeout(() => {
      setShowProgress(false);
    }, 3000);
  } finally {
    setIsFindingVRN(false);
  }
};

  // Handle link to vehicle
  const handleLinkToVehicle = async (vrn, documentIds) => {
    const group = groupedDocs.find(g => g.vrn === vrn);
    if (!group || !group.vehicleDetails) {
      console.error('❌ Vehicle details not found for VRN:', vrn);
      return;
    }

    try {
      console.log('🔗 Batch linking documents to vehicle:', { 
        vrn, 
        vehicleId: group.vehicleDetails.id, 
        documentCount: documentIds.length 
      });

      const result = await ragApi.linkDocumentsToVehicle(group.vehicleDetails.id, documentIds);
      
      console.log('✅ Batch link successful:', result);
      
      // Remove group from list
      setGroupedDocs(prev => prev.filter(g => g.vrn !== vrn));
      
      // Show notification
      showNotification(
        `Successfully linked ${result.linked_count} document(s) to vehicle ${vrn}`,
        'success'
      );
      
      if (result.failed_ids && result.failed_ids.length > 0) {
        alert(`Linked ${result.linked_count} documents. ${result.failed_ids.length} failed.`);
      }
    } catch (err) {
      console.error('❌ Failed to link documents:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Unknown error';
      showNotification(
        `Failed to link documents: ${errorMessage}`,
        'error'
      );
      alert(`Failed to link documents: ${errorMessage}`);
    }
  };

  // Handle create and link
  const handleCreateAndLink = async (vrn, documentIds, vehicleDetails) => {
    try {
      console.log('🚗 Creating vehicle and linking documents:', { 
        vrn, 
        documentCount: documentIds.length,
        vehicleDetails 
      });

      const result = await ragApi.createVehicleAndLinkDocuments(vrn, documentIds, vehicleDetails);
      
      console.log('✅ Vehicle created and documents linked:', result);
      
      // Remove group from list
      setGroupedDocs(prev => prev.filter(g => g.vrn !== vrn));
      
      // Show notification
      showNotification(
        `Successfully created vehicle ${vrn} and linked ${result.linked_count} document(s)`,
        'success'
      );
      
      if (result.failed_ids && result.failed_ids.length > 0) {
        alert(`Vehicle created! Linked ${result.linked_count} documents. ${result.failed_ids.length} failed.`);
      }
    } catch (err) {
      console.error('❌ Failed to create vehicle and link documents:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Unknown error';
      showNotification(
        `Failed to create vehicle: ${errorMessage}`,
        'error'
      );
      alert(`Failed to create vehicle: ${errorMessage}`);
    }
  };

  // Handle manual assign
  const handleManualAssign = async (documentId, vehicleId) => {
    if (!documentId || !vehicleId) {
      console.error('❌ Document ID or Vehicle ID missing');
      return;
    }

    try {
      console.log('🔗 Manually assigning document to vehicle:', { documentId, vehicleId });

      await ragApi.linkDocumentToVehicle(vehicleId, documentId);
      
      console.log('✅ Manual assignment successful');
      
      // Remove document from unassigned list
      setUnassignedDocs(prev => prev.filter(doc => doc.id !== documentId));
      
      // Show notification
      showNotification(
        'Successfully assigned document to vehicle',
        'success'
      );
    } catch (err) {
      console.error('❌ Failed to manually assign document:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Unknown error';
      showNotification(
        `Failed to assign document: ${errorMessage}`,
        'error'
      );
      alert(`Failed to assign document: ${errorMessage}`);
    }
  };

  // ============================================================================
  // RENDER
  // ============================================================================

  if (isLoading) {
    return (
      <div className="loading-state">
        <div className="loading-spinner"></div>
        <p>Loading Document Manager...</p>
      </div>
    );
  }

  if (error && !notification) {
    return (
      <div className="error-state">
        <p className="error-message">{error}</p>
        <button className="retry-button" onClick={fetchData}>
          <FiRefreshCw />
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="doc-manager-container">
      {/* 🆕 NOTIFICATION */}
      {notification && (
        <div className={`notification ${notification.type}`}>
          <span className="notification-icon">
            {notification.type === 'success' ? '✅' : 
             notification.type === 'error' ? '❌' : 'ℹ️'}
          </span>
          <span className="notification-message">{notification.message}</span>
          <button 
            className="notification-close"
            onClick={() => setNotification(null)}
          >
            ×
          </button>
        </div>
      )}

      {/* HEADER WITH ACTIONS */}
      <div className="doc-manager-header">
        <div className="header-title">
          <h1>Document Manager</h1>
          <p className="header-subtitle">
            Organize and assign documents to vehicles
          </p>
        </div>
        
        <div className="header-actions">
          {/* Refresh Button */}
          <button 
            className="refresh-button"
            onClick={fetchData}
            disabled={isLoading || isFindingVRN}
            title="Refresh documents"
          >
            <FiRefreshCw className={isLoading ? 'spinning' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* STATS BAR */}
      <div className="stats-bar">
        <div className="stat-item">
          <span className="stat-label">Need Analysis:</span>
          <span className="stat-value">{processedDocs.length}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Smart Suggestions:</span>
          <span className="stat-value">{groupedDocs.length}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Manual Assignment:</span>
          <span className="stat-value">{unassignedDocs.length}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Total:</span>
          <span className="stat-value">
            {processedDocs.length + groupedDocs.length + unassignedDocs.length}
          </span>
        </div>
      </div>

      {/* 🆕 PROGRESS DISPLAY */}
      {showProgress && findVRNProgress && (
        <FindVRNProgress progress={findVRNProgress} />
      )}

      {/* 🆕 TOP SECTION - PROCESSED DOCUMENTS */}
      <ProcessedDocuments
        documents={processedDocs}
        onFindVRN={handleFindVRN}
        isProcessing={isFindingVRN}
      />

      {/* MAIN CONTENT - 2 COLUMNS */}
      <div className="doc-manager-page">
        {/* LEFT COLUMN - Smart Suggestions (pending_assignment) */}
        <div className="manager-column">
          <div className="column-header">
            <h2>Smart Suggestions</h2>
            {groupedDocs.length > 0 && (
              <span className="column-count">{groupedDocs.length} group{groupedDocs.length !== 1 ? 's' : ''}</span>
            )}
          </div>
          {groupedDocs.length > 0 ? (
            <div className="grouped-list">
              {groupedDocs.map(group => (
                <GroupedDocuments
                  key={group.vrn}
                  group={group}
                  onLink={handleLinkToVehicle}
                  onCreateAndLink={handleCreateAndLink}
                />
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">✅</div>
              <h3>All Clear!</h3>
              <p>No documents with detected VRN waiting to be linked.</p>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN - Manual Assignment (unassigned) */}
        <div className="manager-column">
          <div className="column-header">
            <h2>Manual Assignment</h2>
            {unassignedDocs.length > 0 && (
              <span className="column-count">{unassignedDocs.length} document{unassignedDocs.length !== 1 ? 's' : ''}</span>
            )}
          </div>
          {unassignedDocs.length > 0 ? (
            <UnassignedDocuments 
              documents={unassignedDocs} 
              onAssign={handleManualAssign} 
            />
          ) : (
            <div className="empty-state">
              <div className="empty-icon">🎉</div>
              <h3>Perfect!</h3>
              <p>No documents requiring manual vehicle assignment.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DocumentManagerPage;