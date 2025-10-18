// src/components/buildings/BuildingList.jsx
import React, { useState } from 'react';
import './BuildingList.css';

const BuildingList = ({ buildings, onSelectBuilding, selectedBuildingId, isLoading }) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredBuildings = buildings.filter(b =>
    b.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    b.address.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="building-list-container">
      <div className="list-header">
        <div className="list-title">
          <h3>Properties</h3>
        </div>
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search by name, address..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>
      <div className="list-body">
        {isLoading ? (
          <p>Loading properties...</p>
        ) : (
          <ul className="building-list">
            {filteredBuildings.map(building => (
              <li
                key={building.id}
                className={`building-item ${selectedBuildingId === building.id ? 'active' : ''}`}
                onClick={() => onSelectBuilding(building.id)}
              >
                <div className="building-name">{building.name}</div>
                <div className="building-address">{building.address}</div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default BuildingList;