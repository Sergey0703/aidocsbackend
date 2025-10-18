// src/components/EntityInfo.jsx
import React, { useState } from 'react';
import './EntityInfo.css';

const EntityInfo = ({ entityResult, rewriteResult }) => {
  const [showRewrites, setShowRewrites] = useState(false);

  if (!entityResult) return null;

  return (
    <div className="entity-info">
      <h3>Smart Entity Extraction</h3>
      
      <div className="entity-main">
        <div className="entity-row">
          <span className="label">Original Query:</span>
          <span className="value original">{rewriteResult?.original_query || 'N/A'}</span>
        </div>
        
        <div className="entity-row highlight">
          <span className="label">Extracted Entity:</span>
          <span className="value entity">{entityResult.entity}</span>
        </div>
        
        <div className="entity-row">
          <span className="label">Method:</span>
          <span className="value method">{entityResult.method}</span>
        </div>
        
        <div className="entity-row">
          <span className="label">Confidence:</span>
          <span className="value confidence">
            {(entityResult.confidence * 100).toFixed(1)}%
          </span>
        </div>

        {entityResult.alternatives && entityResult.alternatives.length > 0 && (
          <div className="entity-row">
            <span className="label">Alternatives:</span>
            <span className="value alternatives">
              {entityResult.alternatives.join(', ')}
            </span>
          </div>
        )}
      </div>

      {rewriteResult && rewriteResult.rewrites && rewriteResult.rewrites.length > 0 && (
        <div className="rewrites-section">
          <button 
            className="rewrites-toggle"
            onClick={() => setShowRewrites(!showRewrites)}
          >
            {showRewrites ? '▼' : '▶'} Query Transformations ({rewriteResult.rewrites.length} variants)
          </button>
          
          {showRewrites && (
            <div className="rewrites-list">
              <div className="rewrite-info">
                <span className="rewrite-method">Method: {rewriteResult.method}</span>
                <span className="rewrite-confidence">
                  Confidence: {(rewriteResult.confidence * 100).toFixed(1)}%
                </span>
              </div>
              <ol className="variants-list">
                {rewriteResult.rewrites.map((variant, idx) => (
                  <li key={idx} className="variant-item">
                    {variant}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default EntityInfo;