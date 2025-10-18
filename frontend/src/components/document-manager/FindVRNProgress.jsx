// src/components/document-manager/FindVRNProgress.jsx
import React from 'react';
import './FindVRNProgress.css';
import { FiCheckCircle, FiXCircle, FiAlertCircle, FiLoader } from 'react-icons/fi';

const FindVRNProgress = ({ progress }) => {
  if (!progress) return null;

  const { total, processed, found, notFound, errors, isRunning } = progress;

  // Calculate percentage
  const percentage = total > 0 ? Math.round((processed / total) * 100) : 0;

  // Determine status
  const getStatusMessage = () => {
    if (isRunning) {
      return `Processing document ${processed} of ${total}...`;
    }
    if (errors > 0) {
      return `Completed with ${errors} error(s)`;
    }
    if (found > 0) {
      return `Successfully found VRN in ${found} document(s)!`;
    }
    return 'Processing completed';
  };

  const statusMessage = getStatusMessage();

  return (
    <div className={`find-vrn-progress ${isRunning ? 'running' : 'completed'}`}>
      <div className="progress-header">
        <div className="progress-title">
          {isRunning ? (
            <>
              <FiLoader className="progress-icon spinning" />
              <span>Finding VRN in Documents...</span>
            </>
          ) : (
            <>
              {errors > 0 ? (
                <FiAlertCircle className="progress-icon warning" />
              ) : found > 0 ? (
                <FiCheckCircle className="progress-icon success" />
              ) : (
                <FiXCircle className="progress-icon info" />
              )}
              <span>{statusMessage}</span>
            </>
          )}
        </div>
        <div className="progress-percentage">
          {percentage}%
        </div>
      </div>

      {/* Progress Bar */}
      <div className="progress-bar-container">
        <div 
          className="progress-bar-fill"
          style={{ width: `${percentage}%` }}
        >
          {percentage > 10 && (
            <span className="progress-bar-text">
              {processed} / {total}
            </span>
          )}
        </div>
      </div>

      {/* Statistics */}
      <div className="progress-stats">
        <div className="stat-item success">
          <FiCheckCircle />
          <span className="stat-label">VRN Found:</span>
          <span className="stat-value">{found}</span>
        </div>

        <div className="stat-item info">
          <FiXCircle />
          <span className="stat-label">No VRN:</span>
          <span className="stat-value">{notFound}</span>
        </div>

        {errors > 0 && (
          <div className="stat-item error">
            <FiAlertCircle />
            <span className="stat-label">Errors:</span>
            <span className="stat-value">{errors}</span>
          </div>
        )}
      </div>

      {/* Status Message */}
      <div className="progress-message">
        {isRunning ? (
          <p className="status-running">
            ⏳ Please wait while we analyze your documents using AI...
          </p>
        ) : (
          <p className={`status-${found > 0 ? 'success' : 'info'}`}>
            {found > 0 
              ? '✅ Documents with found VRN have been moved to "Smart Suggestions"'
              : 'ℹ️ No VRN found. Documents remain in "Unassigned Documents" for manual assignment'
            }
          </p>
        )}
      </div>
    </div>
  );
};

export default FindVRNProgress;