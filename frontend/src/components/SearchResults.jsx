// src/components/SearchResults.jsx
import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import DocumentCard from './DocumentCard';
import EntityInfo from './EntityInfo';
import PerformanceMetrics from './PerformanceMetrics';
import './SearchResults.css';
import { FiDatabase, FiCpu, FiFileText } from 'react-icons/fi';

// Component for grouped document display with expandable chunks
const DocumentGroupsSection = ({ results, totalResults }) => {
  const [expandedGroups, setExpandedGroups] = useState({});

  if (!results || results.length === 0) return null;

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

  const toggleGroup = (filename) => {
    setExpandedGroups(prev => ({
      ...prev,
      [filename]: !prev[filename]
    }));
  };

  const getSourceInfo = (method) => {
    if (method && method.includes('database')) return { icon: <FiDatabase />, label: 'Database Match' };
    if (method && method.includes('vector')) return { icon: <FiCpu />, label: 'Vector Match' };
    return { icon: <FiFileText />, label: 'Search Result' };
  };

  return (
    <div className="documents-section">
      <h2 className="section-title">
        Source Documents: {uniqueDocuments} {uniqueDocuments === 1 ? 'document' : 'documents'} ({totalResults} {totalResults === 1 ? 'chunk' : 'chunks'})
      </h2>
      <div className="documents-list">
        {groupedDocs.map((group, index) => {
          const isExpanded = expandedGroups[group.filename];

          return (
            <div key={group.filename} className="document-group">
              <div
                className="document-group-header"
                onClick={() => toggleGroup(group.filename)}
                style={{ cursor: 'pointer' }}
              >
                <span className="document-index">{index + 1}.</span>
                <span className="document-name">{group.filename}</span>
                <span className="chunk-count">
                  {group.chunks.length} {group.chunks.length === 1 ? 'chunk' : 'chunks'}
                </span>
                <span className="document-score">
                  {(group.maxScore * 100).toFixed(1)}%
                </span>
                <span className="expand-indicator">{isExpanded ? '▼' : '▶'}</span>
              </div>

              {isExpanded && (
                <div className="document-chunks-container">
                  {group.chunks.map((chunk, chunkIdx) => {
                    const { icon, label } = getSourceInfo(chunk.source_method);
                    const score = chunk.metadata?.hybrid_weighted_score || chunk.similarity_score || 0;

                    return (
                      <div key={chunkIdx} className="chunk-item">
                        <div className="chunk-header">
                          <span className="chunk-icon">{icon}</span>
                          <span className="chunk-label">Chunk {chunkIdx + 1}</span>
                          <span className="chunk-score">{(score * 100).toFixed(1)}%</span>
                        </div>
                        <div className="chunk-content">
                          <h4>Content:</h4>
                          <div className="markdown-content">
                            <ReactMarkdown>{chunk.content}</ReactMarkdown>
                          </div>
                        </div>
                        <div className="chunk-metadata">
                          <h4>Details:</h4>
                          <div className="metadata-grid">
                            <div className="metadata-item">
                              <span>Source</span>
                              <strong>{label}</strong>
                            </div>
                            <div className="metadata-item">
                              <span>Similarity</span>
                              <strong>{(chunk.similarity_score || 0).toFixed(3)}</strong>
                            </div>
                            <div className="metadata-item">
                              <span>Weighted Score</span>
                              <strong>{(chunk.metadata?.hybrid_weighted_score || 0).toFixed(3)}</strong>
                            </div>
                            <div className="metadata-item">
                              <span>Chunk Index</span>
                              <strong>{chunk.chunk_index || 0}</strong>
                            </div>
                            <div className="metadata-item">
                              <span>Match Type</span>
                              <strong>{chunk.metadata?.match_type || 'N/A'}</strong>
                            </div>
                            <div className="metadata-item">
                              <span>Strategy</span>
                              <strong>{chunk.metadata?.database_strategy || 'Vector'}</strong>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

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
            <ReactMarkdown>{answer}</ReactMarkdown>
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
      <DocumentGroupsSection results={results} totalResults={totalResults} />
    </div>
  );
};

export default SearchResults;