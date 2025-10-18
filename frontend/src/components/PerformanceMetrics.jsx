// src/components/PerformanceMetrics.jsx
import React, { useState } from 'react';
import './PerformanceMetrics.css';

const PerformanceMetrics = ({ metrics }) => {
  const [showDetails, setShowDetails] = useState(false);

  if (!metrics) return null;

  const formatTime = (seconds) => {
    return seconds < 1 ? `${(seconds * 1000).toFixed(0)}ms` : `${seconds.toFixed(2)}s`;
  };

  return (
    <div className="performance-metrics">
      <div className="metrics-header">
        <h3>Performance Analytics</h3>
        <button 
          className="toggle-details"
          onClick={() => setShowDetails(!showDetails)}
        >
          {showDetails ? 'Hide Details' : 'Show Details'}
        </button>
      </div>

      <div className="metrics-summary">
        <div className="metric-card">
          <div className="metric-label">Total Time</div>
          <div className="metric-value">{formatTime(metrics.total_time)}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Extraction</div>
          <div className="metric-value">{formatTime(metrics.extraction_time)}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Retrieval</div>
          <div className="metric-value">{formatTime(metrics.retrieval_time)}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Fusion</div>
          <div className="metric-value">{formatTime(metrics.fusion_time)}</div>
        </div>
      </div>

      {showDetails && (
        <div className="metrics-details">
          <h4>Pipeline Breakdown</h4>
          <div className="pipeline-stages">
            <div className="stage">
              <div className="stage-header">
                <span className="stage-name">Entity Extraction</span>
                <span className="stage-time">{formatTime(metrics.extraction_time)}</span>
                <span className="stage-percent">{metrics.pipeline_efficiency.extraction_pct.toFixed(1)}%</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill extraction"
                  style={{ width: `${metrics.pipeline_efficiency.extraction_pct}%` }}
                />
              </div>
            </div>

            <div className="stage">
              <div className="stage-header">
                <span className="stage-name">Query Rewriting</span>
                <span className="stage-time">{formatTime(metrics.rewrite_time)}</span>
                <span className="stage-percent">{metrics.pipeline_efficiency.rewrite_pct.toFixed(1)}%</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill rewrite"
                  style={{ width: `${metrics.pipeline_efficiency.rewrite_pct}%` }}
                />
              </div>
            </div>

            <div className="stage">
              <div className="stage-header">
                <span className="stage-name">Multi-Retrieval</span>
                <span className="stage-time">{formatTime(metrics.retrieval_time)}</span>
                <span className="stage-percent">{metrics.pipeline_efficiency.retrieval_pct.toFixed(1)}%</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill retrieval"
                  style={{ width: `${metrics.pipeline_efficiency.retrieval_pct}%` }}
                />
              </div>
            </div>

            <div className="stage">
              <div className="stage-header">
                <span className="stage-name">Results Fusion</span>
                <span className="stage-time">{formatTime(metrics.fusion_time)}</span>
                <span className="stage-percent">{metrics.pipeline_efficiency.fusion_pct.toFixed(1)}%</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill fusion"
                  style={{ width: `${metrics.pipeline_efficiency.fusion_pct}%` }}
                />
              </div>
            </div>

            <div className="stage">
              <div className="stage-header">
                <span className="stage-name">Answer Generation</span>
                <span className="stage-time">{formatTime(metrics.answer_time)}</span>
                <span className="stage-percent">{metrics.pipeline_efficiency.answer_pct.toFixed(1)}%</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill answer"
                  style={{ width: `${metrics.pipeline_efficiency.answer_pct}%` }}
                />
              </div>
            </div>
          </div>

          <div className="efficiency-summary">
            <div className="efficiency-metric">
              <span className="efficiency-label">Pipeline Efficiency:</span>
              <span className="efficiency-value">
                {(1 / metrics.total_time).toFixed(2)} queries/sec
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PerformanceMetrics;