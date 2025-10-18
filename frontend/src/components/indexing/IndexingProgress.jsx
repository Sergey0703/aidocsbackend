// src/components/indexing/IndexingProgress.jsx
import React from 'react';
import './IndexingProgress.css';

const IndexingProgress = ({ status, isActive, onStop }) => {
  // Guard clause: return early if no status
  if (!status) {
    return (
      <div className="indexing-progress">
        <div className="no-status-message">
          No indexing status available
        </div>
      </div>
    );
  }

  // Guard clause: check if progress exists
  if (!status.progress) {
    return (
      <div className="indexing-progress">
        <div className="no-status-message">
          Loading indexing status...
        </div>
      </div>
    );
  }

  const { progress, statistics } = status;

  const formatTime = (seconds) => {
    if (!seconds || isNaN(seconds)) return 'N/A';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  const getStatusBadge = () => {
    // Safety check for progress.status
    const statusValue = progress?.status || 'unknown';
    
    switch (statusValue.toLowerCase()) {
      case 'idle':
        return <span className="status-badge idle">⏸️ Idle</span>;
      case 'running':
        return <span className="status-badge running">🔄 Running</span>;
      case 'completed':
        return <span className="status-badge completed">✅ Completed</span>;
      case 'failed':
        return <span className="status-badge failed">❌ Failed</span>;
      case 'cancelled':
        return <span className="status-badge cancelled">🚫 Cancelled</span>;
      default:
        return <span className="status-badge">{statusValue}</span>;
    }
  };

  const getStageIcon = (stage) => {
    if (!stage) return '🔍';
    
    switch (stage.toLowerCase()) {
      case 'conversion': return '🔄';
      case 'loading': return '📂';
      case 'chunking': return '🧩';
      case 'embedding': return '🤖';
      case 'saving': return '💾';
      case 'completed': return '✅';
      default: return '🔍';
    }
  };

  const getCurrentStageDisplay = () => {
    const stage = progress?.stage || progress?.current_stage;
    if (!stage) return 'Initializing...';
    
    const stageName = progress?.current_stage_name || stage;
    return `${getStageIcon(stage)} ${stageName}`;
  };

  // Safe access to progress values with defaults
  const totalFiles = progress?.total_files || 0;
  const processedFiles = progress?.processed_files || 0;
  const failedFiles = progress?.failed_files || 0;
  const totalChunks = progress?.total_chunks || 0;
  const processedChunks = progress?.processed_chunks || 0;
  const processingSpeed = progress?.processing_speed || 0;
  const currentBatch = progress?.current_batch;
  const totalBatches = progress?.total_batches;
  const progressPercentage = progress?.progress_percentage || 0;
  const currentFile = progress?.current_file;
  const elapsedTime = progress?.elapsed_time;
  const estimatedRemaining = progress?.estimated_remaining;
  const avgTimePerFile = progress?.avg_time_per_file;
  const statusValue = progress?.status || 'unknown';

  // Get errors and warnings safely
  const errors = status?.errors || [];
  const warnings = status?.warnings || [];

  return (
    <div className="indexing-progress">
      {/* Status Header */}
      <div className="progress-header">
        <div className="status-info">
          {getStatusBadge()}
          {isActive && (
            <span className="pulse-indicator">
              <span className="pulse-dot"></span>
              Active
            </span>
          )}
        </div>
        <div className="progress-percentage">
          {progressPercentage.toFixed(1)}%
        </div>
      </div>

      {/* Progress Bar */}
      <div className="progress-bar-container">
        <div
          className="progress-bar-fill"
          style={{ width: `${progressPercentage}%` }}
        >
          {progressPercentage > 5 && (
            <span className="progress-bar-text">
              {getCurrentStageDisplay()}
            </span>
          )}
        </div>
      </div>

      {/* Current Processing Info */}
      {currentFile && (
        <div className="current-file">
          <span className="current-file-label">Processing:</span>
          <span className="current-file-name">{currentFile}</span>
        </div>
      )}

      {/* Files & Chunks Progress */}
      <div className="processing-stats">
        <div className="stat-group">
          <div className="stat-header">📄 Files</div>
          <div className="stat-progress">
            <span className="stat-current">{processedFiles}</span>
            <span className="stat-separator">/</span>
            <span className="stat-total">{totalFiles}</span>
          </div>
          {failedFiles > 0 && (
            <div className="stat-failed">❌ {failedFiles} failed</div>
          )}
        </div>

        <div className="stat-group">
          <div className="stat-header">🧩 Chunks</div>
          <div className="stat-progress">
            <span className="stat-current">{processedChunks}</span>
            <span className="stat-separator">/</span>
            <span className="stat-total">{totalChunks}</span>
          </div>
          {processingSpeed > 0 && (
            <div className="stat-speed">
              ⚡ {processingSpeed.toFixed(1)} chunks/s
            </div>
          )}
        </div>

        {currentBatch && totalBatches && (
          <div className="stat-group">
            <div className="stat-header">📦 Batches</div>
            <div className="stat-progress">
              <span className="stat-current">{currentBatch}</span>
              <span className="stat-separator">/</span>
              <span className="stat-total">{totalBatches}</span>
            </div>
          </div>
        )}
      </div>

      {/* Time Information */}
      <div className="time-info">
        <div className="time-item">
          <span className="time-label">⏱️ Elapsed:</span>
          <span className="time-value">{formatTime(elapsedTime)}</span>
        </div>
        {estimatedRemaining && statusValue === 'running' && (
          <div className="time-item">
            <span className="time-label">⏳ Remaining:</span>
            <span className="time-value">{formatTime(estimatedRemaining)}</span>
          </div>
        )}
        {avgTimePerFile > 0 && (
          <div className="time-item">
            <span className="time-label">📊 Avg/File:</span>
            <span className="time-value">{formatTime(avgTimePerFile)}</span>
          </div>
        )}
      </div>

      {/* Statistics (if available) */}
      {statistics && (
        <div className="indexing-statistics">
          <h4>📊 Statistics</h4>
          <div className="stats-grid">
            {statistics.documents_loaded > 0 && (
              <div className="stat-card">
                <div className="stat-card-label">Documents Loaded</div>
                <div className="stat-card-value">{statistics.documents_loaded}</div>
              </div>
            )}
            {statistics.chunks_created > 0 && (
              <div className="stat-card">
                <div className="stat-card-label">Chunks Created</div>
                <div className="stat-card-value">{statistics.chunks_created}</div>
              </div>
            )}
            {statistics.chunks_saved > 0 && (
              <div className="stat-card">
                <div className="stat-card-label">Chunks Saved</div>
                <div className="stat-card-value">{statistics.chunks_saved}</div>
              </div>
            )}
            {statistics.success_rate > 0 && (
              <div className="stat-card success">
                <div className="stat-card-label">Success Rate</div>
                <div className="stat-card-value">{(statistics.success_rate * 100).toFixed(1)}%</div>
              </div>
            )}
            {statistics.gemini_api_calls > 0 && (
              <div className="stat-card api">
                <div className="stat-card-label">Gemini API Calls</div>
                <div className="stat-card-value">{statistics.gemini_api_calls}</div>
              </div>
            )}
            {statistics.gemini_tokens_used > 0 && (
              <div className="stat-card api">
                <div className="stat-card-label">Tokens Used</div>
                <div className="stat-card-value">{statistics.gemini_tokens_used.toLocaleString()}</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Stop Button (if running) */}
      {isActive && onStop && (
        <button className="stop-button" onClick={onStop}>
          🚫 Stop Indexing
        </button>
      )}

      {/* Errors & Warnings */}
      {errors.length > 0 && (
        <div className="errors-section">
          <h4>❌ Errors ({errors.length})</h4>
          <div className="errors-list">
            {errors.slice(0, 5).map((error, index) => (
              <div key={index} className="error-item">
                {error}
              </div>
            ))}
            {errors.length > 5 && (
              <div className="errors-more">
                ... and {errors.length - 5} more errors
              </div>
            )}
          </div>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="warnings-section">
          <h4>⚠️ Warnings ({warnings.length})</h4>
          <div className="warnings-list">
            {warnings.slice(0, 3).map((warning, index) => (
              <div key={index} className="warning-item">
                {warning}
              </div>
            ))}
            {warnings.length > 3 && (
              <div className="warnings-more">
                ... and {warnings.length - 3} more warnings
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default IndexingProgress;