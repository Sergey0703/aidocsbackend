// src/components/common/ConfirmationModal.jsx
import React from 'react';
import './ConfirmationModal.css';

const ConfirmationModal = ({ isOpen, onClose, onConfirm, title, message }) => {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{title}</h3>
        </div>
        <div className="modal-body">
          <p>{message}</p>
        </div>
        <div className="modal-footer">
          <button className="modal-cancel-button" onClick={onClose}>
            Cancel
          </button>
          <button className="modal-confirm-button" onClick={onConfirm}>
            Confirm Delete
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmationModal;