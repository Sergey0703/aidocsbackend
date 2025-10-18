// src/pages/VehiclesPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import './VehiclesPage.css';
import { ragApi } from '../api/ragApi';
import VehicleList from '../components/vehicles/VehicleList';
import VehicleDetail from '../components/vehicles/VehicleDetail';
import CreateVehicleModal from '../components/document-manager/CreateVehicleModal';
import ConfirmationModal from '../components/common/ConfirmationModal';
import { FiSearch, FiAlertCircle } from 'react-icons/fi';

const VehiclesPage = () => {
  // State for vehicles data
  const [vehicles, setVehicles] = useState([]);
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // State for modals
  const [isCreateModalOpen, setCreateModalOpen] = useState(false);
  const [isEditModalOpen, setEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setDeleteModalOpen] = useState(false);
  const [vehicleToDelete, setVehicleToDelete] = useState(null);
  const [vehicleToEdit, setVehicleToEdit] = useState(null);

  // State for operations
  const [isCreating, setIsCreating] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // ========================================================================
  // DATA FETCHING
  // ========================================================================

  const fetchVehicles = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      console.log('📡 Fetching vehicles from backend...');
      const data = await ragApi.getVehicles();
      console.log(`✅ Loaded ${data.length} vehicles`, data);
      setVehicles(data);
    } catch (err) {
      console.error('❌ Failed to load vehicles:', err);
      setError(err.message || "Failed to load vehicles from server.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchVehicles();
  }, [fetchVehicles]);

  // ========================================================================
  // VEHICLE SELECTION
  // ========================================================================

  const handleSelectVehicle = async (vehicleId) => {
    if (selectedVehicle?.id === vehicleId) return; // Already selected

    try {
      console.log(`📡 Fetching details for vehicle: ${vehicleId}`);
      const details = await ragApi.getVehicleDetails(vehicleId);
      console.log('✅ Vehicle details loaded:', details);
      setSelectedVehicle(details);
      setError(null); // Clear any previous errors
    } catch (err) {
      console.error('❌ Failed to load vehicle details:', err);
      setError(err.message || "Failed to load vehicle details.");
      
      // Clear error after 5 seconds
      setTimeout(() => setError(null), 5000);
    }
  };

  // ========================================================================
  // CREATE VEHICLE
  // ========================================================================

  const handleCreateVehicle = async (vehicleData) => {
    setIsCreating(true);
    
    try {
      console.log('📡 Creating new vehicle...', vehicleData);
      const newVehicle = await ragApi.createVehicle(vehicleData);
      console.log('✅ Vehicle created:', newVehicle);
      
      // Add to list
      setVehicles(prev => [newVehicle, ...prev]);
      
      // Close modal
      setCreateModalOpen(false);
      
      // Select the new vehicle
      handleSelectVehicle(newVehicle.id);
      
    } catch (err) {
      console.error('❌ Failed to create vehicle:', err);
      alert(`Failed to create vehicle: ${err.message}`);
    } finally {
      setIsCreating(false);
    }
  };

  // ========================================================================
  // EDIT VEHICLE
  // ========================================================================

  const handleEditRequest = (vehicle) => {
    console.log('🔧 Edit requested for:', vehicle);
    setVehicleToEdit(vehicle);
    setEditModalOpen(true);
  };

  const handleUpdateVehicle = async (vehicleData) => {
    if (!vehicleToEdit) return;
    
    setIsUpdating(true);
    
    try {
      console.log('📡 Updating vehicle...', vehicleData);
      const updatedVehicle = await ragApi.updateVehicle(vehicleToEdit.id, vehicleData);
      console.log('✅ Vehicle updated:', updatedVehicle);
      
      // Update in list
      setVehicles(prev => prev.map(v => 
        v.id === vehicleToEdit.id ? updatedVehicle : v
      ));
      
      // Update selected vehicle if it's the one being edited
      if (selectedVehicle?.id === vehicleToEdit.id) {
        // Reload full details to get updated data
        handleSelectVehicle(vehicleToEdit.id);
      }
      
      // Close modal
      setEditModalOpen(false);
      setVehicleToEdit(null);
      
    } catch (err) {
      console.error('❌ Failed to update vehicle:', err);
      alert(`Failed to update vehicle: ${err.message}`);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleEditCancel = () => {
    setEditModalOpen(false);
    setVehicleToEdit(null);
  };

  // ========================================================================
  // DELETE VEHICLE
  // ========================================================================

  const handleDeleteRequest = (vehicle) => {
    console.log('🗑️ Delete requested for:', vehicle);
    setVehicleToDelete(vehicle);
    setDeleteModalOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!vehicleToDelete) return;

    setIsDeleting(true);
    
    try {
      console.log('📡 Deleting vehicle:', vehicleToDelete.id);
      await ragApi.deleteVehicle(vehicleToDelete.id);
      console.log('✅ Vehicle deleted');
      
      // Remove from list
      setVehicles(prev => prev.filter(v => v.id !== vehicleToDelete.id));
      
      // Clear selection if deleted vehicle was selected
      if (selectedVehicle?.id === vehicleToDelete.id) {
        setSelectedVehicle(null);
      }
      
      // Close modal
      setDeleteModalOpen(false);
      setVehicleToDelete(null);
      
    } catch (err) {
      console.error('❌ Failed to delete vehicle:', err);
      alert(`Failed to delete vehicle: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteModalOpen(false);
    setVehicleToDelete(null);
  };

  // ========================================================================
  // DOCUMENT UNLINKING
  // ========================================================================

  const handleUnlinkDocument = async (documentId) => {
    if (!selectedVehicle) return;

    try {
      console.log('📡 Unlinking document:', documentId);
      await ragApi.unlinkDocumentFromVehicle(documentId, selectedVehicle.id);
      console.log('✅ Document unlinked');
      
      // Optimistically update UI
      setSelectedVehicle(prev => ({
        ...prev,
        documents: prev.documents.filter(doc => doc.id !== documentId),
        total_documents: prev.total_documents - 1,
      }));
      
    } catch (err) {
      console.error('❌ Failed to unlink document:', err);
      alert(`Failed to unlink document: ${err.message}`);
      
      // Reload vehicle details to restore correct state
      handleSelectVehicle(selectedVehicle.id);
    }
  };

  // ========================================================================
  // RENDER
  // ========================================================================

  // Show full-page error if initial load fails
  if (error && !vehicles.length && !isLoading) {
    return (
      <div className="vehicles-page-error">
        <div className="error-container">
          <FiAlertCircle className="error-icon" />
          <h2>Failed to Load Vehicles</h2>
          <p>{error}</p>
          <button 
            className="retry-button"
            onClick={fetchVehicles}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Error banner (for non-critical errors) */}
      {error && vehicles.length > 0 && (
        <div className="error-banner">
          <FiAlertCircle />
          <span>{error}</span>
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {/* Main Content */}
      <div className="vehicles-page">
        {/* Left Column - Vehicle List */}
        <div className="vehicle-list-column">
          <VehicleList
            vehicles={vehicles}
            onSelectVehicle={handleSelectVehicle}
            selectedVehicleId={selectedVehicle?.id}
            onCreateNew={() => setCreateModalOpen(true)}
            isLoading={isLoading}
          />
        </div>

        {/* Right Column - Vehicle Detail */}
        <div className="vehicle-detail-column">
          {selectedVehicle ? (
            <VehicleDetail 
              vehicle={selectedVehicle}
              onDelete={handleDeleteRequest}
              onUnlinkDocument={handleUnlinkDocument}
              onEdit={handleEditRequest}
            />
          ) : (
            <div className="placeholder">
              <FiSearch className="placeholder-icon" />
              <h2>Select a Vehicle</h2>
              <p>Choose a vehicle from the list to view its details and linked documents.</p>
              {vehicles.length === 0 && !isLoading && (
                <button 
                  className="create-first-vehicle-btn"
                  onClick={() => setCreateModalOpen(true)}
                >
                  Create Your First Vehicle
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Create Vehicle Modal */}
      <CreateVehicleModal
        isOpen={isCreateModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onSave={handleCreateVehicle}
        isLoading={isCreating}
      />

      {/* Edit Vehicle Modal */}
      <CreateVehicleModal
        isOpen={isEditModalOpen}
        onClose={handleEditCancel}
        onSave={handleUpdateVehicle}
        initialData={vehicleToEdit}
        isLoading={isUpdating}
      />

      {/* Delete Confirmation Modal */}
      <ConfirmationModal
        isOpen={isDeleteModalOpen}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        title="Delete Vehicle"
        message={
          vehicleToDelete
            ? `Are you sure you want to permanently delete ${vehicleToDelete.registration_number}? ` +
              `This action cannot be undone. All linked documents will be unlinked but not deleted.`
            : ''
        }
        isLoading={isDeleting}
      />
    </>
  );
};

export default VehiclesPage;