// src/api/ragApi.js
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add response interceptor for better error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const ragApi = {
  // ============================================================================
  // SEARCH ENDPOINTS
  // ============================================================================
  
  // Search endpoint
  search: async (query, maxResults = 20) => {
    const response = await api.post('/api/search', {
      query,
      max_results: maxResults,
    });
    return response.data;
  },

  // System status
  getStatus: async () => {
    const response = await api.get('/api/system/status');
    return response.data;
  },

  // Health check
  healthCheck: async () => {
    const response = await api.get('/api/system/health');
    return response.data;
  },

  // ============================================================================
  // CONVERSION ENDPOINTS
  // ============================================================================
  
  // Start document conversion
  startConversion: async (options = {}) => {
    const response = await api.post('/api/conversion/start', {
      input_dir: options.inputDir || null,
      output_dir: options.outputDir || null,
      incremental: options.incremental !== false,
      formats: options.formats || null,
      enable_ocr: options.enableOcr || null,
      max_file_size_mb: options.maxFileSizeMb || null,
    });
    return response.data;
  },

  // Get conversion status
  getConversionStatus: async (taskId) => {
    if (!taskId) {
      throw new Error('Task ID is required');
    }
    const response = await api.get('/api/conversion/status', {
      params: { task_id: taskId }
    });
    return response.data;
  },

  // Get supported formats
  getSupportedFormats: async () => {
    const response = await api.get('/api/conversion/formats');
    return response.data;
  },

  // Get conversion results
  getConversionResults: async (taskId, includeFailed = true, includeSkipped = false) => {
    if (!taskId) {
      throw new Error('Task ID is required');
    }
    const response = await api.get('/api/conversion/results', {
      params: {
        task_id: taskId,
        include_failed: includeFailed,
        include_skipped: includeSkipped
      }
    });
    return response.data;
  },

  // Validate documents
  validateDocuments: async (options = {}) => {
    const response = await api.post('/api/conversion/validate', {
      input_dir: options.inputDir || null,
      check_formats: options.checkFormats !== false,
      check_size: options.checkSize !== false,
      max_size_mb: options.maxSizeMb || null,
    });
    return response.data;
  },

  // Retry failed conversions
  retryFailedConversions: async (taskId) => {
    if (!taskId) {
      throw new Error('Task ID is required');
    }
    const response = await api.post(`/api/conversion/retry?task_id=${taskId}`);
    return response.data;
  },

  // Delete conversion task
  deleteConversionTask: async (taskId) => {
    if (!taskId) {
      throw new Error('Task ID is required');
    }
    const response = await api.delete(`/api/conversion/task/${taskId}`);
    return response.data;
  },

  // Get conversion history
  getConversionHistory: async (limit = 10) => {
    const response = await api.get('/api/conversion/history', {
      params: { limit }
    });
    return response.data;
  },

  // ============================================================================
  // INDEXING ENDPOINTS
  // ============================================================================
  
  // Start indexing
  startIndexing: async (options = {}) => {
    const response = await api.post('/api/indexing/start', {
      mode: options.mode || 'incremental',
      documents_dir: options.documentsDir || null,
      skip_conversion: options.skipConversion || false,
      skip_indexing: options.skipIndexing || false,
      batch_size: options.batchSize || null,
      force_reindex: options.forceReindex || false,
      delete_existing: options.deleteExisting || false,
    });
    return response.data;
  },

  // Stop indexing
  stopIndexing: async (taskId) => {
    if (!taskId) {
      throw new Error('Task ID is required');
    }
    const response = await api.post('/api/indexing/stop', null, {
      params: { task_id: taskId }
    });
    return response.data;
  },

  // Get indexing status
  getIndexingStatus: async (taskId = null) => {
    const params = taskId ? { task_id: taskId } : {};
    const response = await api.get('/api/indexing/status', { params });
    return response.data;
  },

  // Get indexing history
  getIndexingHistory: async (limit = 10) => {
    const response = await api.get('/api/indexing/history', {
      params: { limit }
    });
    return response.data;
  },

  // Clear index
  clearIndex: async (confirm = false) => {
    const response = await api.delete('/api/indexing/clear', {
      params: { confirm }
    });
    return response.data;
  },

  // Reindex specific files
  reindexFiles: async (filenames, force = false) => {
    if (!filenames || filenames.length === 0) {
      throw new Error('At least one filename is required');
    }
    const response = await api.post('/api/indexing/reindex', {
      filenames,
      force
    });
    return response.data;
  },

  // Get all indexing tasks
  getAllIndexingTasks: async () => {
    const response = await api.get('/api/indexing/tasks');
    return response.data;
  },

  // Cleanup completed tasks
  cleanupCompletedTasks: async () => {
    const response = await api.delete('/api/indexing/tasks/cleanup');
    return response.data;
  },

  // ============================================================================
  // DOCUMENTS ENDPOINTS
  // ============================================================================
  
  // List documents
  listDocuments: async (options = {}) => {
    const response = await api.get('/api/documents', {
      params: {
        limit: options.limit || 100,
        offset: options.offset || 0,
        sort_by: options.sortBy || 'indexed_at',
        order: options.order || 'desc'
      }
    });
    return response.data;
  },

  // Get document details
  getDocument: async (filename, includeChunks = false) => {
    if (!filename) {
      throw new Error('Filename is required');
    }
    const response = await api.get(`/api/documents/${encodeURIComponent(filename)}`, {
      params: { include_chunks: includeChunks }
    });
    return response.data;
  },

  // Get document statistics
  getDocumentStats: async () => {
    const response = await api.get('/api/documents/stats/overview');
    return response.data;
  },

  // Search documents
  searchDocuments: async (criteria) => {
    const response = await api.post('/api/documents/search', criteria);
    return response.data;
  },

  // Delete document
  deleteDocument: async (filename, deleteChunks = true) => {
    if (!filename) {
      throw new Error('Filename is required');
    }
    const response = await api.delete(`/api/documents/${encodeURIComponent(filename)}`, {
      params: { delete_chunks: deleteChunks }
    });
    return response.data;
  },

  // Get document chunks
  getDocumentChunks: async (filename, limit = 100, offset = 0) => {
    if (!filename) {
      throw new Error('Filename is required');
    }
    const response = await api.get(`/api/documents/${encodeURIComponent(filename)}/chunks`, {
      params: { limit, offset }
    });
    return response.data;
  },

  // Upload document
  uploadDocument: async (file, autoIndex = true) => {
    if (!file) {
      throw new Error('File is required');
    }
    const formData = new FormData();
    formData.append('file', file);
    formData.append('auto_index', autoIndex);

    const response = await api.post('/api/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Get missing documents
  getMissingDocuments: async () => {
    const response = await api.get('/api/documents/missing/files');
    return response.data;
  },

  // ============================================================================
  // MONITORING ENDPOINTS
  // ============================================================================
  
  getPipelineStatus: async (taskId = null) => {
    const params = taskId ? { task_id: taskId } : {};
    const response = await api.get('/api/monitoring/pipeline', { params });
    return response.data;
  },

  getPerformanceMetrics: async (taskId = null) => {
    const params = taskId ? { task_id: taskId } : {};
    const response = await api.get('/api/monitoring/performance', { params });
    return response.data;
  },

  getErrorLogs: async (options = {}) => {
    const response = await api.get('/api/monitoring/errors', {
      params: {
        limit: options.limit || 50,
        error_type: options.errorType || null,
        since: options.since || null
      }
    });
    return response.data;
  },

  getProcessingQueue: async () => {
    const response = await api.get('/api/monitoring/queue');
    return response.data;
  },

  getChunkAnalysis: async () => {
    const response = await api.get('/api/monitoring/chunks/analysis');
    return response.data;
  },

  getDatabaseStats: async () => {
    const response = await api.get('/api/monitoring/database/stats');
    return response.data;
  },

  getMonitoringHealth: async () => {
    const response = await api.get('/api/monitoring/health');
    return response.data;
  },

  getMetricsSummary: async () => {
    const response = await api.get('/api/monitoring/metrics/summary');
    return response.data;
  },
  
  // ============================================================================
  // VEHICLES MODULE
  // ============================================================================

  // Get list of all vehicles
  getVehicles: async (params = {}) => {
    const response = await api.get('/api/vehicles', {
      params: {
        status: params.status || null,
        page: params.page || 1,
        page_size: params.pageSize || 100
      }
    });
    return response.data.vehicles || [];
  },

  // Get full details for a single vehicle, including its documents
  getVehicleDetails: async (vehicleId) => {
    if (!vehicleId) {
      throw new Error('Vehicle ID is required');
    }
    const response = await api.get(`/api/vehicles/${vehicleId}`);
    
    return {
      ...response.data.vehicle,
      documents: response.data.documents || [],
      total_documents: response.data.total_documents || 0,
    };
  },

  // Create a new vehicle
  createVehicle: async (vehicleData) => {
    const response = await api.post('/api/vehicles', {
      registration_number: vehicleData.registration_number,
      vin_number: vehicleData.vin_number || null,
      make: vehicleData.make || null,
      model: vehicleData.model || null,
      insurance_expiry_date: vehicleData.insurance_expiry_date || null,
      motor_tax_expiry_date: vehicleData.motor_tax_expiry_date || null,
      nct_expiry_date: vehicleData.nct_expiry_date || null,
      status: vehicleData.status || 'active',
      current_driver_id: vehicleData.current_driver_id || null,
    });
    return response.data;
  },

  // Update a vehicle's data
  updateVehicle: async (vehicleId, vehicleData) => {
    if (!vehicleId) {
      throw new Error('Vehicle ID is required');
    }
    const response = await api.put(`/api/vehicles/${vehicleId}`, vehicleData);
    return response.data;
  },

  // Delete a vehicle
  deleteVehicle: async (vehicleId) => {
    if (!vehicleId) {
      throw new Error('Vehicle ID is required');
    }
    const response = await api.delete(`/api/vehicles/${vehicleId}`);
    return response.data;
  },

  // Get vehicle statistics
  getVehicleStatistics: async () => {
    const response = await api.get('/api/vehicles/stats/overview');
    return response.data;
  },

  // ============================================================================
  // DOCUMENT LINKING (OLD ENDPOINTS - KEPT FOR COMPATIBILITY)
  // ============================================================================

  // Get unassigned documents (status='unassigned')
  getUnassignedDocuments: async () => {
    const response = await api.get('/api/vehicles/documents/unassigned');
    return response.data;
  },

  // 🆕 UPDATED: Analyze documents (NEW STRUCTURE)
  analyzeDocuments: async () => {
    const response = await api.get('/api/vehicles/documents/analyze');
    return response.data;
  },

  // Get document statistics
  getDocumentStatistics: async () => {
    const response = await api.get('/api/vehicles/documents/stats');
    return response.data;
  },

  // 🆕 Get documents by status
  getDocumentsByStatus: async (status, limit = 100) => {
    const response = await api.get('/api/vehicles/documents/by-status', {
      params: { status, limit }
    });
    return response.data;
  },

  // ============================================================================
  // 🆕 DOCUMENT INBOX MODULE - NEW BATCH ENDPOINTS
  // ============================================================================

  // Batch link documents to vehicle
  inboxLinkBatch: async (vehicleId, registryIds) => {
    if (!vehicleId || !registryIds || registryIds.length === 0) {
      throw new Error('Vehicle ID and at least one registry ID are required');
    }
    const response = await api.post(`/api/inbox/link-batch?vehicle_id=${vehicleId}`, {
      registry_ids: registryIds
    });
    return response.data;
  },

  // Batch unlink documents
  inboxUnlinkBatch: async (registryIds) => {
    if (!registryIds || registryIds.length === 0) {
      throw new Error('At least one registry ID is required');
    }
    const response = await api.post('/api/inbox/unlink-batch', {
      registry_ids: registryIds
    });
    return response.data;
  },

  // Create vehicle and link documents in one operation
  inboxCreateAndLink: async (registrationNumber, documentIds, vehicleDetails = {}) => {
    if (!registrationNumber || !documentIds || documentIds.length === 0) {
      throw new Error('Registration number and at least one document ID are required');
    }
    const response = await api.post('/api/inbox/create-vehicle-and-link', {
      registration_number: registrationNumber,
      make: vehicleDetails.make || null,
      model: vehicleDetails.model || null,
      vin_number: vehicleDetails.vin_number || null,
      insurance_expiry_date: vehicleDetails.insurance_expiry_date || null,
      motor_tax_expiry_date: vehicleDetails.motor_tax_expiry_date || null,
      nct_expiry_date: vehicleDetails.nct_expiry_date || null,
      status: vehicleDetails.status || 'active',
      document_ids: documentIds
    });
    return response.data;
  },

  // Search vehicles for dropdown autocomplete
  inboxSearchVehicles: async (query = '', limit = 10) => {
    const response = await api.get('/api/inbox/search-vehicles', {
      params: { query, limit }
    });
    return response.data;
  },

  // 🆕 FIND VRN IN DOCUMENTS - NEW ENDPOINT
  findVRNInDocuments: async (documentIds = null, useAi = true) => {
    try {
      console.log('🔍 Calling findVRNInDocuments API...');
      
      const response = await api.post('/api/inbox/find-vrn', {
        document_ids: documentIds,
        use_ai: useAi
      });
      
      console.log('✅ findVRNInDocuments response:', response.data);
      
      return response.data;
    } catch (error) {
      console.error('❌ findVRNInDocuments error:', error);
      throw error;
    }
  },

  // ============================================================================
  // 📄 UPDATED LEGACY WRAPPERS - NOW USE NEW BATCH ENDPOINTS
  // ============================================================================

  // Link single document to vehicle (uses old endpoint for single operations)
  linkDocumentToVehicle: async (vehicleId, documentId) => {
    if (!vehicleId || !documentId) {
      throw new Error('Vehicle ID and Document ID are required');
    }
    const response = await api.post(`/api/vehicles/${vehicleId}/documents/link`, {
      registry_id: documentId
    });
    return response.data;
  },

  // Unlink single document from vehicle (uses old endpoint)
  unlinkDocumentFromVehicle: async (documentId, vehicleId) => {
    if (!vehicleId || !documentId) {
      throw new Error('Vehicle ID and Document ID are required');
    }
    const response = await api.post(`/api/vehicles/${vehicleId}/documents/unlink`, {
      registry_id: documentId
    });
    return response.data;
  },

  // 🆕 UPDATED: Wrapper for document manager - NOW USES NEW STRUCTURE
  getUnassignedAndGroupedDocuments: async () => {
    return await ragApi.analyzeDocuments();
  },

  // 🆕 UPDATED: Bulk linking - NOW USES NEW BATCH ENDPOINT
  linkDocumentsToVehicle: async (vehicleId, documentIds) => {
    if (!vehicleId || !documentIds || documentIds.length === 0) {
      throw new Error('Vehicle ID and at least one document ID are required');
    }

    try {
      // Use new batch endpoint instead of loop
      const result = await ragApi.inboxLinkBatch(vehicleId, documentIds);
      
      return {
        success: result.success,
        message: result.message,
        linked_count: result.linked_count,
        failed_ids: result.failed_ids || []
      };
    } catch (error) {
      console.error('Batch linking failed:', error);
      throw error;
    }
  },

  // 🆕 UPDATED: Create vehicle and link - NOW USES NEW ENDPOINT
  createVehicleAndLinkDocuments: async (vrn, documentIds, vehicleDetails = {}) => {
    if (!vrn || !documentIds || documentIds.length === 0) {
      throw new Error('VRN and at least one document ID are required');
    }

    try {
      // Use new create-and-link endpoint
      const result = await ragApi.inboxCreateAndLink(vrn, documentIds, vehicleDetails);
      
      return {
        success: result.success,
        message: result.message,
        vehicle: result.vehicle,
        linked_count: result.linked_count,
        failed_ids: result.failed_ids || []
      };
    } catch (error) {
      console.error('Create and link failed:', error);
      throw error;
    }
  },

  // Get vehicles list (legacy wrapper)
  getVehiclesList: async () => {
    return await ragApi.getVehicles();
  },
};

// Export default
export default ragApi;