// src/components/ErrorDisplay.jsx
import React from 'react';
import './ErrorDisplay.css';
import { FiAlertCircle, FiAlertTriangle, FiInfo, FiRefreshCw, FiMail } from 'react-icons/fi';

const ErrorDisplay = ({ error, onRetry, severity = 'error' }) => {
  if (!error) return null;

  // Determine icon and styling based on severity
  const getSeverityConfig = () => {
    switch (severity) {
      case 'warning':
        return {
          icon: <FiAlertTriangle />,
          className: 'error-display warning',
          title: 'Warning'
        };
      case 'info':
        return {
          icon: <FiInfo />,
          className: 'error-display info',
          title: 'Information'
        };
      case 'error':
      default:
        return {
          icon: <FiAlertCircle />,
          className: 'error-display error',
          title: 'Error'
        };
    }
  };

  const config = getSeverityConfig();

  // Determine if error is recoverable (user can retry)
  const isRecoverable = () => {
    const recoverableMessages = [
      'timeout',
      'timed out',
      'unable to connect',
      'temporarily unavailable',
      'try again'
    ];
    const errorLower = error.toLowerCase();
    return recoverableMessages.some(msg => errorLower.includes(msg));
  };

  // Determine if user should contact support
  const shouldContactSupport = () => {
    const supportMessages = [
      'unexpected error',
      'contact support',
      'has been notified'
    ];
    const errorLower = error.toLowerCase();
    return supportMessages.some(msg => errorLower.includes(msg));
  };

  return (
    <div className={config.className}>
      <div className="error-header">
        <span className="error-icon">{config.icon}</span>
        <h3 className="error-title">{config.title}</h3>
      </div>

      <div className="error-message">
        <p>{error}</p>
      </div>

      <div className="error-actions">
        {isRecoverable() && onRetry && (
          <button className="btn-retry" onClick={onRetry}>
            <FiRefreshCw />
            Try Again
          </button>
        )}

        {shouldContactSupport() && (
          <a
            href="mailto:support@example.com?subject=RAG Search Error"
            className="btn-support"
          >
            <FiMail />
            Contact Support
          </a>
        )}
      </div>

      {/* Help text for common errors */}
      {error.toLowerCase().includes('no results found') && (
        <div className="error-help">
          <h4>Suggestions:</h4>
          <ul>
            <li>Check spelling and try different keywords</li>
            <li>Use more general search terms</li>
            <li>Try searching by vehicle registration number (e.g., '191-D-12345')</li>
          </ul>
        </div>
      )}

      {error.toLowerCase().includes('invalid input') && (
        <div className="error-help">
          <h4>Tips:</h4>
          <ul>
            <li>Avoid special characters like &lt;, &gt;, or SQL keywords</li>
            <li>Keep queries under 1000 characters</li>
            <li>Use simple, descriptive search terms</li>
          </ul>
        </div>
      )}

      {error.toLowerCase().includes('timeout') && (
        <div className="error-help">
          <h4>This search took too long. Try:</h4>
          <ul>
            <li>Using fewer or simpler keywords</li>
            <li>Searching for more specific terms</li>
            <li>Waiting a moment and trying again</li>
          </ul>
        </div>
      )}
    </div>
  );
};

export default ErrorDisplay;
