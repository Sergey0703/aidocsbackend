// src/components/indexing/ConversionProgress.jsx
import React from 'react';
import './ConversionProgress.css';

const ConversionProgress = ({ status, isActive }) => {
  // Guard clause: return early if no status
  if (!status) {
    return (
      <div className="conversion-progress">
        <div className="no-status-message">
          No conversion status available
        </div>
      </div>
    );
  }

  // Guard clause: check if progress exists
  if (!status.progress) {
    return (
      <div className="conversion-progress">
        <div className="no-status-message">
          Loading conversion status...
        </div>
      </div>
    );
  }

  const { progress } = status;

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
      case 'pending':
        return <span className="status-badge pending">⏳ Pending</span>;
      case 'converting':
        return <span className="status-badge converting">🔄 Converting</span>;
      case 'completed':
        return <span className="status-badge completed">✅ Completed</span>;
      case 'failed':
        return <span className="status-badge failed">❌ Failed</span>;
      default:
        return <span className="status-badge">{statusValue}</span>;
    }
  };

  const getProgressColor = () => {
    const failedFiles = progress?.failed_files || 0;
    const statusValue = progress?.status || '';
    
    if (failedFiles > 0) return '#dc3545';
    if (statusValue === 'completed') return '#28a745';
    return '#007bff';
  };

  // Safe access to progress values with defaults
  const totalFiles = progress?.total_files || 0;
  const convertedFiles = progress?.converted_files || 0;
  const failedFiles = progress?.failed_files || 0;
  const skippedFiles = progress?.skipped_files || 0;
  const progressPercentage = progress?.progress_percentage || 0;
  const currentFile = progress?.current_file;
  const elapsedTime = progress?.elapsed_time;
  const estimatedRemaining = progress?.estimated_remaining;
  const statusValue = progress?.status || 'unknown';

  // Calculate processed files
  const processedFiles = convertedFiles + failedFiles + skippedFiles;

  // Get results safely
  const results = status?.results || [];

  return (
    <div className="conversion-progress">
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
          style={{
            width: `${progressPercentage}%`,
            backgroundColor: getProgressColor()
          }}
        >
          {progressPercentage > 5 && (
            <span className="progress-bar-text">
              {processedFiles} / {totalFiles}
            </span>
          )}
        </div>
      </div>

      {/* Current File */}
      {currentFile && (
        <div className="current-file">
          <span className="current-file-label">Converting:</span>
          <span className="current-file-name">{currentFile}</span>
        </div>
      )}

      {/* Statistics Grid */}
      <div className="conversion-stats">
        <div className="stat-item">
          <div className="stat-icon">📊</div>
          <div className="stat-content">
            <div className="stat-label">Total Files</div>
            <div className="stat-value">{totalFiles}</div>
          </div>
        </div>

        <div className="stat-item success">
          <div className="stat-icon">✅</div>
          <div className="stat-content">
            <div className="stat-label">Converted</div>
            <div className="stat-value">{convertedFiles}</div>
          </div>
        </div>

        <div className="stat-item error">
          <div className="stat-icon">❌</div>
          <div className="stat-content">
            <div className="stat-label">Failed</div>
            <div className="stat-value">{failedFiles}</div>
          </div>
        </div>

        <div className="stat-item skipped">
          <div className="stat-icon">⏩</div>
          <div className="stat-content">
            <div className="stat-label">Skipped</div>
            <div className="stat-value">{skippedFiles}</div>
          </div>
        </div>
      </div>

      {/* Time Information */}
      <div className="time-info">
        <div className="time-item">
          <span className="time-label">⏱️ Elapsed:</span>
          <span className="time-value">{formatTime(elapsedTime)}</span>
        </div>
        {estimatedRemaining && statusValue === 'converting' && (
          <div className="time-item">
            <span className="time-label">⏳ Remaining:</span>
            <span className="time-value">{formatTime(estimatedRemaining)}</span>
          </div>
        )}
      </div>

      {/* Results List (if completed or failed) */}
      {(statusValue === 'completed' || statusValue === 'failed') && results.length > 0 && (
        <div className="conversion-results">
          <h4>Conversion Results:</h4>
          <div className="results-list">
            {results.slice(0, 10).map((result, index) => {
              // Safe access to result properties
              const resultStatus = result?.status || 'unknown';
              const resultFilename = result?.filename || 'Unknown file';
              const resultError = result?.error_message;
              const resultTime = result?.conversion_time;

              return (
                <div key={index} className={`result-item ${resultStatus}`}>
                  <div className="result-icon">
                    {resultStatus === 'completed' ? '✅' : '❌'}
                  </div>
                  <div className="result-info">
                    <div className="result-filename">{resultFilename}</div>
                    {resultError && (
                      <div className="result-error">{resultError}</div>
                    )}
                    {resultTime && (
                      <div className="result-time">
                        {formatTime(resultTime)}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            {results.length > 10 && (
              <div className="results-more">
                ... and {results.length - 10} more
              </div>
            )}
          </div>
        </div>
      )}

      {/* Error Messages */}
      {status.errors && status.errors.length > 0 && (
        <div className="conversion-errors">
          <h4>⚠️ Errors:</h4>
          <div className="errors-list">
            {status.errors.map((error, index) => (
              <div key={index} className="error-item">
                {error}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ConversionProgress;