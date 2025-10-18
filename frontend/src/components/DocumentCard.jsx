// src/components/DocumentCard.jsx
import React, { useState } from 'react';
import './DocumentCard.css';
import { FiDatabase, FiCpu, FiFileText } from 'react-icons/fi';

const DocumentCard = ({ doc, index }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getSourceInfo = (method) => {
    if (method.includes('database')) return { icon: <FiDatabase />, label: 'Database Match' };
    if (method.includes('vector')) return { icon: <FiCpu />, label: 'Vector Match' };
    return { icon: <FiFileText />, label: 'Search Result' };
  };

  const { icon, label } = getSourceInfo(doc.source_method);
  const score = doc.metadata.hybrid_weighted_score || doc.similarity_score;

  return (
    <div className="doc-card">
      <header className="doc-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="doc-title">
          <span className="doc-index">{index}.</span>
          <span className="doc-icon">{icon}</span>
          <span className="doc-filename">{doc.filename}</span>
        </div>
        <div className="doc-score-container">
          <span className="doc-score">{(score * 100).toFixed(1)}%</span>
          <button className="doc-expand-btn">{isExpanded ? '▲' : '▼'}</button>
        </div>
      </header>

      {isExpanded && (
        <section className="doc-content">
          <div className="doc-preview">
            <h4>Content Preview:</h4>
            <p>{doc.content}</p>
          </div>
          <div className="doc-metadata">
            <h4>Intelligence Details:</h4>
            <div className="metadata-grid">
              <div className="metadata-item"><span>Source</span><strong>{label}</strong></div>
              <div className="metadata-item"><span>Similarity</span><strong>{doc.similarity_score.toFixed(3)}</strong></div>
              <div className="metadata-item"><span>Weighted Score</span><strong>{(doc.metadata.hybrid_weighted_score || 0).toFixed(3)}</strong></div>
              <div className="metadata-item"><span>Chunk</span><strong>{doc.chunk_index}</strong></div>
              <div className="metadata-item"><span>Match Type</span><strong>{doc.metadata.match_type || 'N/A'}</strong></div>
              <div className="metadata-item"><span>Strategy</span><strong>{doc.metadata.database_strategy || 'Vector'}</strong></div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};

export default DocumentCard;