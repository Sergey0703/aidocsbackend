// src/components/document-manager/VehicleSearchInput.jsx
import React, { useState, useEffect, useRef, useCallback } from 'react';
import './VehicleSearchInput.css';
import { FiSearch, FiTruck, FiX } from 'react-icons/fi';
import { ragApi } from '../../api/ragApi';

const VehicleSearchInput = ({ 
  onSelect, 
  placeholder = "Search vehicles by registration number...",
  disabled = false,
  autoFocus = false 
}) => {
  // State
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [error, setError] = useState(null);

  // Refs
  const inputRef = useRef(null);
  const dropdownRef = useRef(null);
  const debounceTimerRef = useRef(null);

  // Auto-focus if requested
  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        dropdownRef.current && 
        !dropdownRef.current.contains(event.target) &&
        inputRef.current &&
        !inputRef.current.contains(event.target)
      ) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced search function
  const performSearch = useCallback(async (query) => {
    if (!query || query.trim().length < 1) {
      setSearchResults([]);
      setIsDropdownOpen(false);
      return;
    }

    setIsSearching(true);
    setError(null);

    try {
      const response = await ragApi.inboxSearchVehicles(query, 10);
      setSearchResults(response.results || []);
      setIsDropdownOpen(true);
      setSelectedIndex(-1);
    } catch (err) {
      console.error('Search failed:', err);
      setError('Failed to search vehicles');
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  // Handle input change with debounce
  const handleInputChange = (e) => {
    const value = e.target.value;
    setSearchQuery(value);

    // Clear previous timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Set new timer
    debounceTimerRef.current = setTimeout(() => {
      performSearch(value);
    }, 300); // 300ms debounce
  };

  // Handle vehicle selection
  const handleSelectVehicle = (vehicle) => {
    console.log('🚗 Vehicle selected:', vehicle);
    
    // Update input to show selected vehicle
    setSearchQuery(`${vehicle.registration_number} (${vehicle.make} ${vehicle.model})`);
    
    // Close dropdown
    setIsDropdownOpen(false);
    
    // Reset selection index
    setSelectedIndex(-1);
    
    // Call parent callback
    onSelect(vehicle);
    
    // Clear search after selection
    setTimeout(() => {
      setSearchQuery('');
      setSearchResults([]);
    }, 100);
  };

  // Handle clear button
  const handleClear = () => {
    setSearchQuery('');
    setSearchResults([]);
    setIsDropdownOpen(false);
    setSelectedIndex(-1);
    setError(null);
    
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  // Keyboard navigation
  const handleKeyDown = (e) => {
    if (!isDropdownOpen || searchResults.length === 0) {
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < searchResults.length - 1 ? prev + 1 : prev
        );
        break;

      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => prev > 0 ? prev - 1 : -1);
        break;

      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < searchResults.length) {
          handleSelectVehicle(searchResults[selectedIndex]);
        }
        break;

      case 'Escape':
        e.preventDefault();
        setIsDropdownOpen(false);
        setSelectedIndex(-1);
        break;

      default:
        break;
    }
  };

  // Render status icon
  const renderStatusIcon = () => {
    if (isSearching) {
      return <div className="search-spinner" />;
    }
    if (searchQuery && !isSearching) {
      return (
        <button 
          className="clear-button" 
          onClick={handleClear}
          type="button"
          aria-label="Clear search"
        >
          <FiX />
        </button>
      );
    }
    return <FiSearch className="search-icon" />;
  };

  return (
    <div className="vehicle-search-container">
      {/* Search Input */}
      <div className="vehicle-search-input-wrapper">
        <input
          ref={inputRef}
          type="text"
          className="vehicle-search-input"
          value={searchQuery}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete="off"
        />
        <div className="search-icon-wrapper">
          {renderStatusIcon()}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="search-error">
          {error}
        </div>
      )}

      {/* Dropdown Results */}
      {isDropdownOpen && searchResults.length > 0 && (
        <div 
          ref={dropdownRef} 
          className="vehicle-search-dropdown"
        >
          {searchResults.map((vehicle, index) => (
            <div
              key={vehicle.id}
              className={`search-result-item ${index === selectedIndex ? 'selected' : ''}`}
              onClick={() => handleSelectVehicle(vehicle)}
              onMouseEnter={() => setSelectedIndex(index)}
            >
              <div className="result-icon">
                <FiTruck />
              </div>
              <div className="result-info">
                <div className="result-vrn">{vehicle.registration_number}</div>
                <div className="result-details">
                  {vehicle.make && vehicle.model 
                    ? `${vehicle.make} ${vehicle.model}`
                    : vehicle.make || vehicle.model || 'Unknown vehicle'
                  }
                </div>
              </div>
              <div className={`result-status status-${vehicle.status}`}>
                {vehicle.status}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* No Results */}
      {isDropdownOpen && searchResults.length === 0 && !isSearching && searchQuery.length > 0 && (
        <div ref={dropdownRef} className="vehicle-search-dropdown">
          <div className="search-no-results">
            <FiSearch />
            <p>No vehicles found matching "{searchQuery}"</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default VehicleSearchInput;