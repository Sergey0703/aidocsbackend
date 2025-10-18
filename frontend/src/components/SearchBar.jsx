// src/components/SearchBar.jsx
import React, { useState } from 'react';
import './SearchBar.css';

const SearchBar = ({ onSearch, isLoading }) => {
  const [query, setQuery] = useState('');
  const [maxResults, setMaxResults] = useState(20);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSearch(query, maxResults);
    }
  };

  return (
    <div className="search-bar-wrapper">
      <form onSubmit={handleSubmit} className="search-form">
        <div className="search-input-container">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter your question (e.g., tell me about...)"
            className="search-input"
            disabled={isLoading}
          />
        </div>
        <div className="search-controls">
          <input
            type="number"
            value={maxResults}
            onChange={(e) => setMaxResults(Number(e.target.value))}
            min="1"
            max="100"
            className="max-results-input"
            disabled={isLoading}
            title="Max results"
          />
          <button 
            type="submit" 
            className="search-button"
            disabled={isLoading || !query.trim()}
          >
            {isLoading ? 'Searching...' : 'Hybrid Search'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default SearchBar;