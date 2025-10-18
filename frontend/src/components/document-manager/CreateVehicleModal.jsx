// src/components/document-manager/CreateVehicleModal.jsx
import React, { useState, useEffect } from 'react';
import './CreateVehicleModal.css';

const CreateVehicleModal = ({ isOpen, onClose, onSave, vrn, initialData, isLoading }) => {
  const [formData, setFormData] = useState({
    registration_number: '',
    make: '',
    model: '',
    vin_number: '',
    insurance_expiry_date: '',
    motor_tax_expiry_date: '',
    nct_expiry_date: '',
    status: 'active',
  });

  const [errors, setErrors] = useState({});

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      console.log('🔧 Modal opened. initialData:', initialData);
      
      // Если есть initialData с id - это режим редактирования
      if (initialData && initialData.id) {
        console.log('📝 EDIT MODE - filling form with:', initialData);
        setFormData({
          registration_number: initialData.registration_number || '',
          make: initialData.make || '',
          model: initialData.model || '',
          vin_number: initialData.vin_number || '',
          insurance_expiry_date: initialData.insurance_expiry_date || '',
          motor_tax_expiry_date: initialData.motor_tax_expiry_date || '',
          nct_expiry_date: initialData.nct_expiry_date || '',
          status: initialData.status || 'active',
        });
      } else {
        // Режим создания - пустая форма
        console.log('➕ CREATE MODE - empty form');
        setFormData({
          registration_number: vrn || '',
          make: '',
          model: '',
          vin_number: '',
          insurance_expiry_date: '',
          motor_tax_expiry_date: '',
          nct_expiry_date: '',
          status: 'active',
        });
      }
      setErrors({});
    }
  }, [isOpen, initialData, vrn]);

  if (!isOpen) {
    return null;
  }

  const handleChange = (e) => {
    const { name, value } = e.target;
    console.log('🔄 Field changed:', name, '=', value);
    setFormData(prev => ({ ...prev, [name]: value }));
    
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: null }));
    }
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.registration_number || !formData.registration_number.trim()) {
      newErrors.registration_number = 'Registration number is required';
    }

    if (!formData.make || !formData.make.trim()) {
      newErrors.make = 'Make is required';
    }

    if (!formData.model || !formData.model.trim()) {
      newErrors.model = 'Model is required';
    }

    if (formData.vin_number && formData.vin_number.trim().length > 0) {
      if (formData.vin_number.trim().length !== 17) {
        newErrors.vin_number = 'VIN must be exactly 17 characters';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    const submitData = {
      registration_number: formData.registration_number.trim(),
      make: formData.make.trim(),
      model: formData.model.trim(),
      vin_number: formData.vin_number.trim() || null,
      insurance_expiry_date: formData.insurance_expiry_date || null,
      motor_tax_expiry_date: formData.motor_tax_expiry_date || null,
      nct_expiry_date: formData.nct_expiry_date || null,
      status: formData.status,
    };

    onSave(submitData);
  };

  // Определяем заголовки и текст кнопок
  const isEditMode = initialData && initialData.id;
  console.log('🏷️ Modal title calculation:', { initialData, isEditMode, hasId: initialData?.id });
  const modalTitle = isEditMode ? `Edit Vehicle: ${initialData.registration_number}` : 'Create New Vehicle';
  const submitButtonText = isEditMode ? 'Update Vehicle' : 'Create Vehicle';

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{modalTitle}</h3>
          <button className="modal-close-button" onClick={onClose}>
            &times;
          </button>
        </div>

        <div className="modal-body">
          <form onSubmit={handleSubmit} id="create-vehicle-form">
            <div className="form-group">
              <label htmlFor="registration_number">
                Registration Number <span className="required">*</span>
              </label>
              <input
                type="text"
                id="registration_number"
                name="registration_number"
                value={formData.registration_number}
                onChange={handleChange}
                placeholder="e.g., 191-D-12345"
                autoComplete="off"
              />
              {errors.registration_number && (
                <span className="error-message">{errors.registration_number}</span>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="make">
                Make <span className="required">*</span>
              </label>
              <input
                type="text"
                id="make"
                name="make"
                value={formData.make}
                onChange={handleChange}
                placeholder="e.g., Toyota"
                autoComplete="off"
              />
              {errors.make && (
                <span className="error-message">{errors.make}</span>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="model">
                Model <span className="required">*</span>
              </label>
              <input
                type="text"
                id="model"
                name="model"
                value={formData.model}
                onChange={handleChange}
                placeholder="e.g., Yaris"
                autoComplete="off"
              />
              {errors.model && (
                <span className="error-message">{errors.model}</span>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="vin_number">VIN Number (Optional)</label>
              <input
                type="text"
                id="vin_number"
                name="vin_number"
                value={formData.vin_number}
                onChange={handleChange}
                placeholder="17-character VIN"
                maxLength={17}
                autoComplete="off"
              />
              {errors.vin_number && (
                <span className="error-message">{errors.vin_number}</span>
              )}
              <span className="field-hint">Must be exactly 17 characters</span>
            </div>

            <div className="form-group">
              <label htmlFor="status">Status</label>
              <select
                id="status"
                name="status"
                value={formData.status}
                onChange={handleChange}
              >
                <option value="active">Active</option>
                <option value="maintenance">Maintenance</option>
                <option value="inactive">Inactive</option>
                <option value="sold">Sold</option>
                <option value="archived">Archived</option>
              </select>
            </div>

            <div className="form-section-header">
              <h4>Expiry Dates (Optional)</h4>
            </div>

            <div className="form-group">
              <label htmlFor="insurance_expiry_date">Insurance Expiry Date</label>
              <input
                type="date"
                id="insurance_expiry_date"
                name="insurance_expiry_date"
                value={formData.insurance_expiry_date}
                onChange={handleChange}
              />
            </div>

            <div className="form-group">
              <label htmlFor="motor_tax_expiry_date">Motor Tax Expiry Date</label>
              <input
                type="date"
                id="motor_tax_expiry_date"
                name="motor_tax_expiry_date"
                value={formData.motor_tax_expiry_date}
                onChange={handleChange}
              />
            </div>

            <div className="form-group">
              <label htmlFor="nct_expiry_date">NCT Expiry Date</label>
              <input
                type="date"
                id="nct_expiry_date"
                name="nct_expiry_date"
                value={formData.nct_expiry_date}
                onChange={handleChange}
              />
            </div>
          </form>
        </div>

        <div className="modal-footer">
          <button className="modal-cancel-button" onClick={onClose}>
            Cancel
          </button>
          <button className="modal-save-button" onClick={handleSubmit}>
            {submitButtonText}
          </button>
        </div>
      </div>
    </div>
  );
};

export default CreateVehicleModal;