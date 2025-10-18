// src/pages/BuildingsPage.jsx
import React, { useState, useEffect } from 'react';
import './BuildingsPage.css';
import { mockBuildings } from '../api/mockData';
import BuildingList from '../components/buildings/BuildingList';
import BuildingDetail from '../components/buildings/BuildingDetail';
import { FiSearch } from 'react-icons/fi';

const BuildingsPage = () => {
  const [buildings, setBuildings] = useState([]);
  const [selectedBuilding, setSelectedBuilding] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Simulate fetching data
    setIsLoading(true);
    setTimeout(() => {
      setBuildings(mockBuildings);
      setIsLoading(false);
    }, 500); // 0.5 second delay to simulate network
  }, []);

  const handleSelectBuilding = (buildingId) => {
    if (selectedBuilding?.id === buildingId) return;

    const buildingDetails = buildings.find(b => b.id === buildingId);
    setSelectedBuilding(buildingDetails);
  };

  return (
    <div className="buildings-page">
      {/* Left Column - Building List */}
      <div className="building-list-column">
        <BuildingList
          buildings={buildings}
          onSelectBuilding={handleSelectBuilding}
          selectedBuildingId={selectedBuilding?.id}
          isLoading={isLoading}
        />
      </div>

      {/* Right Column - Building Detail */}
      <div className="building-detail-column">
        {selectedBuilding ? (
          <BuildingDetail building={selectedBuilding} />
        ) : (
          <div className="placeholder">
            <FiSearch className="placeholder-icon" />
            <h2>Select a Property</h2>
            <p>Choose a property from the list to view its details and linked documents.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default BuildingsPage;