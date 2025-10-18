// src/components/indexing/PipelineStages.jsx
import React from 'react';
import './PipelineStages.css';

const PipelineStages = ({ status }) => {
  if (!status || !status.progress) return null;

  const { progress, statistics } = status;

  const stages = [
    {
      name: 'Loading',
      icon: '📂',
      key: 'loading',
      description: 'Loading & Preparing Docs',
      completed: !!statistics?.documents_loaded || progress.stage !== 'loading',
      active: progress.stage === 'loading' || progress.current_stage_name === "Checking for updates",
      count: statistics?.documents_loaded || 0
    },
    {
      name: 'Chunking',
      icon: '🧩',
      key: 'chunking',
      description: 'Creating text chunks',
      completed: !!statistics?.chunks_created,
      active: progress.stage === 'chunking',
      count: statistics?.chunks_created || 0
    },
    {
      name: 'Embedding',
      icon: '🤖',
      key: 'embedding',
      description: 'Generating embeddings',
      completed: progress.processed_chunks > 0 && progress.stage !== 'embedding',
      active: progress.stage === 'embedding',
      count: progress.processed_chunks || 0
    },
    {
      name: 'Saving',
      icon: '💾',
      key: 'saving',
      description: 'Saving to vector database',
      completed: !!statistics?.chunks_saved && progress.status === 'completed',
      active: progress.stage === 'saving',
      count: statistics?.chunks_saved || 0
    }
  ];

  const getStageStatus = (stage) => {
    // If the overall task is finished, no stage can be 'active'.
    // It's either 'completed' if it was passed, or 'pending'.
    if (progress.status === 'completed' || progress.status === 'failed' || progress.status === 'cancelled') {
        return stage.completed ? 'completed' : 'pending';
    }
    
    // Otherwise, use the active logic
    if (stage.active) return 'active';
    if (stage.completed) return 'completed';
    return 'pending';
  };

  return (
    <div className="pipeline-stages">
      <div className="stages-container">
        {stages.map((stage, index) => (
          <React.Fragment key={stage.key}>
            <div className={`stage ${getStageStatus(stage)}`}>
              <div className="stage-icon">{stage.icon}</div>
              <div className="stage-content">
                <div className="stage-name">{stage.name}</div>
                <div className="stage-description">{stage.description}</div>
                {(getStageStatus(stage) !== 'pending') && stage.count > 0 && (
                  <div className="stage-count">
                    {stage.count.toLocaleString()} {stage.key === 'loading' ? 'docs' : 'chunks'}
                  </div>
                )}
                <div className="stage-status-indicator">
                  {getStageStatus(stage) === 'completed' && <span className="status-icon completed">✅</span>}
                  {getStageStatus(stage) === 'active' && (
                    <span className="status-icon active">
                      <span className="spinner"></span>
                    </span>
                  )}
                  {getStageStatus(stage) === 'pending' && (
                    <span className="status-icon pending">⏸️</span>
                  )}
                </div>
              </div>
            </div>
            
            {index < stages.length - 1 && (
              <div className={`stage-connector ${getStageStatus(stages[index + 1]) !== 'pending' ? 'active' : ''}`}>
                <div className="connector-line"></div>
                <div className="connector-arrow">→</div>
              </div>
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Overall Progress Summary */}
      {progress.status !== 'idle' && (
        <div className="pipeline-summary">
          <div className="summary-item">
            <span className="summary-label">Overall Progress:</span>
            <span className="summary-value">{progress.progress_percentage.toFixed(1)}%</span>
          </div>
          {statistics?.success_rate > 0 && (
            <div className="summary-item">
              <span className="summary-label">Success Rate:</span>
              <span className="summary-value success">
                {statistics.success_rate.toFixed(1)}%
              </span>
            </div>
          )}
          {statistics?.gemini_api_calls > 0 && (
            <div className="summary-item">
              <span className="summary-label">Gemini API Calls:</span>
              <span className="summary-value api">
                {statistics.gemini_api_calls.toLocaleString()}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PipelineStages;