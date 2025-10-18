// src/components/SearchResults.jsx
import React, { useState } from 'react';
import DocumentCard from './DocumentCard';
import EntityInfo from './EntityInfo';
import PerformanceMetrics from './PerformanceMetrics';
import './SearchResults.css';

const SearchResults = ({ results, answer, totalResults, entityResult, rewriteResult, performanceMetrics }) => {
  const [showEntity, setShowEntity] = useState(false);
  const [showPerformance, setShowPerformance] = useState(false);

  if (!answer && totalResults === 0) {
    return (
      <div className="search-results-container">
        <div className="answer-section">
          <h2 className="section-title">Answer</h2>
          <div className="answer-box fallback">
            <p>{answer || "No relevant information was found based on your query."}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="search-results-container">
      {/* Answer Section */}
      {answer && (
        <div className="answer-section">
          <h2 className="section-title">Answer</h2>
          <div className="answer-box">
            {answer.split('\n').map((line, idx) => (
              <p key={idx} style={{ margin: '0.5rem 0' }}>{line}</p>
            ))}
          </div>
        </div>
      )}

      {/* Accordion for Details */}
      <div className="details-accordion">
        <div className="accordion-item">
          <button className="accordion-toggle" onClick={() => setShowEntity(!showEntity)}>
            <span>{showEntity ? '▼' : '▶'}</span>
            Smart Entity Extraction
          </button>
          {showEntity && (
            <div className="accordion-content">
              <EntityInfo entityResult={entityResult} rewriteResult={rewriteResult} />
            </div>
          )}
        </div>
        <div className="accordion-item">
          <button className="accordion-toggle" onClick={() => setShowPerformance(!showPerformance)}>
            <span>{showPerformance ? '▼' : '▶'}</span>
            Performance Analytics
          </button>
          {showPerformance && (
            <div className="accordion-content">
              <PerformanceMetrics metrics={performanceMetrics} />
            </div>
          )}
        </div>
      </div>

      {/* Source Documents Section */}
      {results && results.length > 0 && (
        <div className="documents-section">
          <h2 className="section-title">Source Documents ({totalResults})</h2>
          <div className="documents-list">
            {results.map((doc, index) => (
              <DocumentCard key={`${doc.document_id}-${index}`} doc={doc} index={index + 1} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchResults;