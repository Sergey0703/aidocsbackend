// src/components/SystemStatus.jsx
import React, { useState, useEffect } from 'react';
import { ragApi } from '../api/ragApi';
import './SystemStatus.css';
// ИСПРАВЛЕНИЕ: Заменены FiBrain и FiRocket на существующие иконки
import { FiRefreshCw, FiDatabase, FiCpu, FiZap } from 'react-icons/fi';

const SystemStatus = ({ lastSearchMetrics }) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const data = await ragApi.getStatus();
      setStatus(data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch system status.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const formatTime = (seconds) => {
    if (seconds === undefined || seconds === null) return 'N/A';
    return seconds < 1 ? `${(seconds * 1000).toFixed(0)}ms` : `${seconds.toFixed(2)}s`;
  };

  const StatusItem = ({ icon, title, isAvailable, details }) => (
    <div className="status-item">
      <div className={`status-icon ${isAvailable ? 'ok' : 'error'}`}>
        {isAvailable ? '✓' : '✗'}
      </div>
      <div className="status-content">
        <div className="status-title">{title}</div>
        {details && <div className="status-details">{details}</div>}
      </div>
    </div>
  );

  return (
    <div className="system-status-card">
      <div className="card-header">
        <h3>System Status</h3>
        <button onClick={fetchStatus} disabled={loading} className="refresh-button">
          <FiRefreshCw className={loading ? 'spinning' : ''} />
        </button>
      </div>

      {loading && <div className="status-loading">Checking system...</div>}
      {error && <div className="status-error-msg">{error}</div>}

      {status && (
        <div className="status-body">
          {status.hybrid_enabled && (
            <div className="status-badge hybrid-enabled">
              <FiZap /> Hybrid Search Enabled
            </div>
          )}
          
          <div className="status-section">
            <StatusItem 
              icon={<FiDatabase />} 
              title="Database" 
              isAvailable={status.database.available}
              details={status.database.available ? `${status.database.unique_files} files` : status.database.error}
            />
            <StatusItem 
              icon={<FiCpu />} 
              title="Embeddings" 
              isAvailable={status.embedding.available}
              details={status.embedding.available ? `${status.embedding.model}` : status.embedding.error}
            />
          </div>

          {lastSearchMetrics && (
            <div className="status-section">
              {/* ИСПРАВЛЕНИЕ: FiRocket заменен на FiZap */}
              <h4><FiZap /> Last Search</h4>
              <div className="last-search-metrics">
                <div className="metric-item">
                  <span>Total:</span>
                  <span>{formatTime(lastSearchMetrics.total_time)}</span>
                </div>
                <div className="metric-item">
                  <span>Extraction:</span>
                  <span>{formatTime(lastSearchMetrics.extraction_time)}</span>
                </div>
                <div className="metric-item">
                  <span>Retrieval:</span>
                  <span>{formatTime(lastSearchMetrics.retrieval_time)}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SystemStatus;