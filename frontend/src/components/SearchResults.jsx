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
      {results && results.length > 0 && (() => {
        // Group chunks by document filename
        const docGroups = {};
        results.forEach(doc => {
          const filename = doc.file_name || doc.filename;
          if (!filename) return;

          if (!docGroups[filename]) {
            docGroups[filename] = {
              filename: filename,
              chunks: [],
              maxScore: 0
            };
          }

          docGroups[filename].chunks.push(doc);
          // Track highest score for this document
          const score = doc.score || doc.similarity_score || 0;
          if (score > docGroups[filename].maxScore) {
            docGroups[filename].maxScore = score;
          }
        });

        // Convert to array and sort by max score (descending)
        const groupedDocs = Object.values(docGroups).sort((a, b) => b.maxScore - a.maxScore);
        const uniqueDocuments = groupedDocs.length;

        return (
          <div className="documents-section">
            <h2 className="section-title">
              Source Documents: {uniqueDocuments} {uniqueDocuments === 1 ? 'document' : 'documents'} ({totalResults} {totalResults === 1 ? 'chunk' : 'chunks'})
            </h2>
            <div className="documents-list">
              {groupedDocs.map((group, index) => (
                <div key={group.filename} className="document-group">
                  <div className="document-group-header">
                    <span className="document-index">{index + 1}.</span>
                    <span className="document-name">{group.filename}</span>
                    <span className="chunk-count">
                      {group.chunks.length} {group.chunks.length === 1 ? 'chunk' : 'chunks'}
                    </span>
                    <span className="document-score">
                      {(group.maxScore * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })()}
    </div>
  );
};

export default SearchResults;