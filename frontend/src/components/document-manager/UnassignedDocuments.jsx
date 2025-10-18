// src/components/document-manager/UnassignedDocuments.jsx
import React, { useState, useEffect } from 'react';
import './UnassignedDocuments.css';
import { ragApi } from '../../api/ragApi';
import { FiFileText, FiSearch } from 'react-icons/fi';

const UnassignedDocuments = ({ documents, onAssign }) => {
  const [vehicles, setVehicles] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoadingVehicles, setIsLoadingVehicles] = useState(false);
  const [selectedVehicles, setSelectedVehicles] = useState({});

  // Fetch vehicles for dropdown
  useEffect(() => {
    const fetchVehicles = async () => {
      setIsLoadingVehicles(true);
      try {
        const vehiclesList = await ragApi.getVehiclesList();
        setVehicles(vehiclesList || []);
      } catch (error) {
        console.error('Failed to fetch vehicles:', error);
        setVehicles([]);
      } finally {
        setIsLoadingVehicles(false);
      }
    };

    fetchVehicles();
  }, []);

  // Search vehicles
  const searchVehicles = async (query) => {
    if (!query || query.length < 2) {
      // Reset to all vehicles if search is cleared
      try {
        const vehiclesList = await ragApi.getVehiclesList();
        setVehicles(vehiclesList || []);
      } catch (error) {
        console.error('Failed to fetch vehicles:', error);
      }
      return;
    }

    try {
      const result = await ragApi.inboxSearchVehicles(query, 20);
      setVehicles(result.results || []);
    } catch (error) {
      console.error('Search failed:', error);
    }
  };

  // Handle search input change
  const handleSearchChange = (e) => {
    const query = e.target.value;
    setSearchQuery(query);
    
    // Debounce search
    clearTimeout(window.vehicleSearchTimeout);
    window.vehicleSearchTimeout = setTimeout(() => {
      searchVehicles(query);
    }, 300);
  };

  // Handle vehicle selection
  const handleVehicleSelect = (docId, vehicleId) => {
    setSelectedVehicles(prev => ({
      ...prev,
      [docId]: vehicleId
    }));
  };

  // Handle assign button click
  const handleAssign = async (docId) => {
    const vehicleId = selectedVehicles[docId];
    if (!vehicleId) {
      alert('Please select a vehicle first');
      return;
    }

    await onAssign(docId, vehicleId);
    
    // Clear selection after assignment
    setSelectedVehicles(prev => {
      const newState = { ...prev };
      delete newState[docId];
      return newState;
    });
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

  if (documents.length === 0) {
    return (
      <div className="unassigned-empty">
        <div className="empty-icon">🎉</div>
        <h3>All Clear!</h3>
        <p>No documents requiring manual assignment.</p>
      </div>
    );
  }

  return (
    <div className="unassigned-documents">
      {/* Vehicle Search */}
      <div className="vehicle-search-section">
        <div className="search-input-wrapper">
          <FiSearch className="search-icon" />
          <input
            type="text"
            className="vehicle-search-input"
            placeholder="Search vehicles by registration number..."
            value={searchQuery}
            onChange={handleSearchChange}
          />
        </div>
        {isLoadingVehicles && (
          <div className="loading-hint">Loading vehicles...</div>
        )}
      </div>

      {/* Documents List */}
      <div className="unassigned-list">
        {documents.map((doc) => (
          <div key={doc.id} className="unassigned-item">
            <div className="unassigned-header">
              <div className="document-icon">
                <FiFileText />
              </div>
              <div className="document-info">
                <div className="document-name">
                  {getFileName(doc.raw_file_path)}
                </div>
                <div className="document-meta">
                  <span className="document-date">
                    {formatDate(doc.uploaded_at)}
                  </span>
                  <span className="document-status">
                    No VRN detected
                  </span>
                </div>
              </div>
            </div>

            <div className="assignment-section">
              <select
                className="vehicle-select"
                value={selectedVehicles[doc.id] || ''}
                onChange={(e) => handleVehicleSelect(doc.id, e.target.value)}
              >
                <option value="">Select a vehicle...</option>
                {vehicles.map((vehicle) => (
                  <option key={vehicle.id} value={vehicle.id}>
                    {vehicle.registration_number}
                    {vehicle.make && vehicle.model && ` - ${vehicle.make} ${vehicle.model}`}
                  </option>
                ))}
              </select>

              <button
                className="assign-button"
                onClick={() => handleAssign(doc.id)}
                disabled={!selectedVehicles[doc.id]}
              >
                Assign
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Footer hint */}
      <div className="unassigned-footer">
        <p className="footer-hint">
          💡 These documents had no VRN detected. Manually select a vehicle to assign them.
        </p>
      </div>
    </div>
  );
};

export default UnassignedDocuments;