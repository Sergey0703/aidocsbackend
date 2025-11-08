// src/components/SearchBar.jsx
import React, { useState, useEffect, useRef } from 'react';
import { FiClock, FiX } from 'react-icons/fi';
import './SearchBar.css';

const HISTORY_KEY = 'search_history';
const MAX_HISTORY_ITEMS = 10;

const SearchBar = ({ onSearch, isLoading }) => {
  const [query, setQuery] = useState('');
  const [maxResults, setMaxResults] = useState(20);
  const [searchHistory, setSearchHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const inputRef = useRef(null);
  const historyRef = useRef(null);

  // Load search history from localStorage on mount
  useEffect(() => {
    const savedHistory = localStorage.getItem(HISTORY_KEY);
    if (savedHistory) {
      try {
        setSearchHistory(JSON.parse(savedHistory));
      } catch (e) {
        console.error('Failed to load search history:', e);
      }
    }
  }, []);

  // Save search history to localStorage
  const saveToHistory = (searchQuery) => {
    if (!searchQuery.trim()) return;

    setSearchHistory((prevHistory) => {
      // Remove duplicate if exists
      const filtered = prevHistory.filter(item => item !== searchQuery);
      // Add to beginning
      const newHistory = [searchQuery, ...filtered].slice(0, MAX_HISTORY_ITEMS);
      // Save to localStorage
      localStorage.setItem(HISTORY_KEY, JSON.stringify(newHistory));
      return newHistory;
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      saveToHistory(query);
      onSearch(query, maxResults);
      setShowHistory(false);
    }
  };

  const handleHistoryClick = (historyQuery) => {
    setQuery(historyQuery);
    setShowHistory(false);
    inputRef.current?.focus();
  };

  const handleClearHistory = () => {
    setSearchHistory([]);
    localStorage.removeItem(HISTORY_KEY);
    setShowHistory(false);
  };

  // Handle keyboard navigation
  const handleKeyDown = (e) => {
    if (!showHistory || searchHistory.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setFocusedIndex((prev) =>
        prev < searchHistory.length - 1 ? prev + 1 : prev
      );
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setFocusedIndex((prev) => (prev > 0 ? prev - 1 : -1));
    } else if (e.key === 'Enter' && focusedIndex >= 0) {
      e.preventDefault();
      handleHistoryClick(searchHistory[focusedIndex]);
    } else if (e.key === 'Escape') {
      setShowHistory(false);
      setFocusedIndex(-1);
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        historyRef.current &&
        !historyRef.current.contains(event.target) &&
        !inputRef.current?.contains(event.target)
      ) {
        setShowHistory(false);
        setFocusedIndex(-1);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="search-bar-wrapper">
      <form onSubmit={handleSubmit} className="search-form">
        <div className="search-input-container">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => searchHistory.length > 0 && setShowHistory(true)}
            onKeyDown={handleKeyDown}
            placeholder="Enter your question (e.g., tell me about...)"
            className="search-input"
            disabled={isLoading}
            autoComplete="off"
          />

          {/* Search History Dropdown */}
          {showHistory && searchHistory.length > 0 && (
            <div ref={historyRef} className="search-history-dropdown">
              <div className="search-history-header">
                <span className="search-history-title">
                  <FiClock /> Recent Searches
                </span>
                <button
                  type="button"
                  className="clear-history-button"
                  onClick={handleClearHistory}
                  title="Clear history"
                >
                  <FiX /> Clear
                </button>
              </div>
              <ul className="search-history-list">
                {searchHistory.map((item, index) => (
                  <li
                    key={index}
                    className={`search-history-item ${
                      index === focusedIndex ? 'focused' : ''
                    }`}
                    onClick={() => handleHistoryClick(item)}
                    onMouseEnter={() => setFocusedIndex(index)}
                  >
                    <FiClock className="history-icon" />
                    <span className="history-text">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
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