// src/components/vehicles/VehicleList.jsx
import React, { useState } from 'react';
import './VehicleList.css';
import { FiPlus } from 'react-icons/fi';

const VehicleList = ({ vehicles, onSelectVehicle, selectedVehicleId, onCreateNew, isLoading }) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredVehicles = vehicles.filter(v =>
    v.registration_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
    v.make.toLowerCase().includes(searchTerm.toLowerCase()) ||
    v.model.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="vehicle-list-container">
      <div className="list-header">
        <div className="list-title">
          <h3>Vehicle Fleet</h3>
          <button className="create-vehicle-btn" onClick={onCreateNew}>
            <FiPlus /> New Vehicle
          </button>
        </div>
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search by VRN, make..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>
      <div className="list-body">
        {isLoading ? (
          <p>Loading fleet...</p>
        ) : (
          <ul className="vehicle-list">
            {filteredVehicles.map(vehicle => (
              <li
                key={vehicle.id}
                className={`vehicle-item ${selectedVehicleId === vehicle.id ? 'active' : ''}`}
                onClick={() => onSelectVehicle(vehicle.id)}
              >
                <div className="vrn">{vehicle.registration_number}</div>
                <div className="make-model">{vehicle.make} {vehicle.model}</div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default VehicleList;