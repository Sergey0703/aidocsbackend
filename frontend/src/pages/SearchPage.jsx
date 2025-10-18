// src/pages/SearchPage.jsx
import React, { useState } from 'react';
import { ragApi } from '../api/ragApi';
import SearchBar from '../components/SearchBar';
import SystemStatus from '../components/SystemStatus';
import SearchResults from '../components/SearchResults';
import './SearchPage.css';

const SearchPage = () => {
  const [searchResults, setSearchResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [rerankMode, setRerankMode] = useState('smart');
  const [hasSearched, setHasSearched] = useState(false); // Новое состояние для отслеживания поиска

  const handleSearch = async (query, maxResults) => {
    setIsLoading(true);
    setError(null);
    setSearchResults(null);
    setHasSearched(true); // Устанавливаем, что поиск был выполнен

    try {
      const data = await ragApi.search(query, maxResults, rerankMode);
      setSearchResults(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'An unknown error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  // ИЗМЕНЕНИЕ: Компонент WelcomeMessage удален.
  // Вместо него будет отображаться сообщение о результатах или их отсутствии.

  return (
    <div className="search-page">
      <div className="search-page-left-column">
        <SystemStatus
          lastSearchMetrics={searchResults?.performance_metrics}
          rerankMode={rerankMode}
          onRerankModeChange={setRerankMode}
        />
      </div>

      <div className="search-page-main-column">
        <SearchBar onSearch={handleSearch} isLoading={isLoading} />

        {isLoading && <div className="loading-indicator">Searching...</div>}
        {error && <div className="error-message">{error}</div>}
        
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