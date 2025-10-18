// src/components/indexing/DocumentsList.jsx
import React, { useState } from 'react';
import './DocumentsList.css';
import DocumentCard from './DocumentCard';

const DocumentsList = ({ documents, loading, onDelete, onRefresh }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('indexed_at');
  const [sortOrder, setSortOrder] = useState('desc');

  if (loading) {
    return (
      <div className="documents-loading">
        <div className="loading-spinner"></div>
        <p>Loading documents...</p>
      </div>
    );
  }

  if (!documents || documents.length === 0) {
    return (
      <div className="documents-empty">
        <div className="empty-icon">📭</div>
        <h3>No Documents Indexed</h3>
        <p>Upload and index documents to see them here.</p>
      </div>
    );
  }

  // Filter documents by search query
  const filteredDocuments = documents.filter(doc =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Sort documents
  const sortedDocuments = [...filteredDocuments].sort((a, b) => {
    let comparison = 0;

    switch (sortBy) {
      case 'filename':
        comparison = a.filename.localeCompare(b.filename);
        break;
      case 'chunks':
        comparison = a.total_chunks - b.total_chunks;
        break;
      case 'indexed_at':
        const dateA = a.indexed_at ? new Date(a.indexed_at) : new Date(0);
        const dateB = b.indexed_at ? new Date(b.indexed_at) : new Date(0);
        comparison = dateA - dateB;
        break;
      default:
        comparison = 0;
    }

    return sortOrder === 'desc' ? -comparison : comparison;
  });

  const handleSortChange = (newSortBy) => {
    if (sortBy === newSortBy) {
      // Toggle order if same column
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(newSortBy);
      setSortOrder('desc');
    }
  };

  return (
    <div className="documents-list">
      {/* Search and Sort Controls */}
      <div className="list-controls">
        <div className="search-box">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
          {searchQuery && (
            <button
              className="clear-search"
              onClick={() => setSearchQuery('')}
              title="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        <div className="sort-controls">
          <label>Sort by:</label>
          <button
            className={`sort-button ${sortBy === 'indexed_at' ? 'active' : ''}`}
            onClick={() => handleSortChange('indexed_at')}
          >
            Date {sortBy === 'indexed_at' && (sortOrder === 'desc' ? '↓' : '↑')}
          </button>
          <button
            className={`sort-button ${sortBy === 'filename' ? 'active' : ''}`}
            onClick={() => handleSortChange('filename')}
          >
            Name {sortBy === 'filename' && (sortOrder === 'desc' ? '↓' : '↑')}
          </button>
          <button
            className={`sort-button ${sortBy === 'chunks' ? 'active' : ''}`}
            onClick={() => handleSortChange('chunks')}
          >
            Chunks {sortBy === 'chunks' && (sortOrder === 'desc' ? '↓' : '↑')}
          </button>
        </div>
      </div>

      {/* Results Count */}
      <div className="results-info">
        {searchQuery ? (
          <span>
            Found {sortedDocuments.length} of {documents.length} documents
          </span>
        ) : (
          <span>
            Showing {sortedDocuments.length} documents
          </span>
        )}
      </div>

      {/* Documents List */}
      {sortedDocuments.length > 0 ? (
        <div className="documents-grid">
          {sortedDocuments.map((doc) => (
            <DocumentCard
              key={doc.filename}
              document={doc}
              onDelete={onDelete}
            />
          ))}
        </div>
      ) : (
        <div className="no-results">
          <div className="no-results-icon">🔍</div>
          <p>No documents match your search</p>
          <button onClick={() => setSearchQuery('')} className="clear-search-button">
            Clear Search
          </button>
        </div>
      )}
    </div>
  );
};

export default DocumentsList;