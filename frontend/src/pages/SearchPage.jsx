// src/pages/SearchPage.jsx
import React, { useState } from 'react';
import { ragApi } from '../api/ragApi';
import SearchBar from '../components/SearchBar';
import SystemStatus from '../components/SystemStatus';
import SearchResults from '../components/SearchResults';
import ErrorDisplay from '../components/ErrorDisplay';
import './SearchPage.css';

const SearchPage = () => {
  const [searchResults, setSearchResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastQuery, setLastQuery] = useState(null);
  const [lastMaxResults, setLastMaxResults] = useState(null);
  const [hasSearched, setHasSearched] = useState(false); // Новое состояние для отслеживания поиска

  const handleSearch = async (query, maxResults) => {
    setIsLoading(true);
    setError(null);
    setSearchResults(null);
    setHasSearched(true); // Устанавливаем, что поиск был выполнен
    setLastQuery(query);
    setLastMaxResults(maxResults);

    try {
      const data = await ragApi.search(query, maxResults);
      setSearchResults(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'An unknown error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetry = () => {
    if (lastQuery) {
      handleSearch(lastQuery, lastMaxResults);
    }
  };

  // ИЗМЕНЕНИЕ: Компонент WelcomeMessage удален.
  // Вместо него будет отображаться сообщение о результатах или их отсутствии.

  return (
    <div className="search-page">
      <div className="search-page-left-column">
        <SystemStatus
          lastSearchMetrics={searchResults?.performance_metrics}
        />
      </div>

      <div className="search-page-main-column">
        <SearchBar onSearch={handleSearch} isLoading={isLoading} />

        {isLoading && <div className="loading-indicator">Searching...</div>}

        {/* NEW: Enhanced error display with retry functionality */}
        {error && (
          <ErrorDisplay
            error={error}
            onRetry={handleRetry}
            severity="error"
          />
        )}

        {/* ИЗМЕНЕНИЕ: Обновленная логика отображения */}
        {hasSearched && !isLoading && !error && (
          <SearchResults
            results={searchResults?.results}
            answer={searchResults?.answer}
            totalResults={searchResults?.total_results}
            entityResult={searchResults?.entity_result}
            rewriteResult={searchResults?.rewrite_result}
            performanceMetrics={searchResults?.performance_metrics}
          />
        )}
      </div>
    </div>
  );
};

export default SearchPage;