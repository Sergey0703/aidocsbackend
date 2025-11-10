// src/pages/IndexingPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import './IndexingPage.css';
import { ragApi } from '../api/ragApi';
import FileUploader from '../components/indexing/FileUploader';
import ConversionProgress from '../components/indexing/ConversionProgress';
import IndexingProgress from '../components/indexing/IndexingProgress';

const IndexingPage = () => {
  // --- STATE MANAGEMENT ---

  // Состояния для отслеживания активных процессов
  const [isUploading, setIsUploading] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [isIndexing, setIsIndexing] = useState(false);

  // ID задач для опроса статуса
  const [conversionTaskId, setConversionTaskId] = useState(null);
  const [indexingTaskId, setIndexingTaskId] = useState(null);

  // Объекты со статусами от API
  const [conversionStatus, setConversionStatus] = useState(null);
  const [indexingStatus, setIndexingStatus] = useState(null);

  // Состояния для статистики документов
  const [docStats, setDocStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(true);

  // Настройки для загрузки и индексации
  const [uploadSettings, setUploadSettings] = useState({
    incremental: true,
    enableOcr: true,
    maxFileSizeMb: 50,
  });

  // Сообщения для пользователя
  // eslint-disable-next-line no-unused-vars
  const [error, setError] = useState(null);
  const [indexingResult, setIndexingResult] = useState(null);
  const [uploadMessage, setUploadMessage] = useState(null); // {type: 'info'|'warning'|'error', message: string}

  // --- DATA FETCHING ---

  const fetchDocumentStats = useCallback(async () => {
    setLoadingStats(true);
    try {
      const data = await ragApi.getDocumentStats();
      setDocStats(data);
    } catch (err) {
      console.error("Failed to fetch document statistics:", err);
      setError("Could not load document statistics.");
    } finally {
      setLoadingStats(false);
    }
  }, []);

  // Первоначальная загрузка статистики
  useEffect(() => {
    fetchDocumentStats();
  }, [fetchDocumentStats]);


  // --- LOGIC FOR POLLING STATUSES ---

  const handleStartIndexing = useCallback(async () => {
    setError(null);
    setIndexingResult(null);
    setIndexingStatus(null);
    setIsIndexing(true);

    try {
      const response = await ragApi.startIndexing({
        mode: 'incremental', // Можно будет добавить в UI
        skipConversion: true, // Мы уже сделали конвертацию
      });
      setIndexingTaskId(response.task_id);
    } catch (err) {
      console.error('Failed to start indexing:', err);
      setError(err.response?.data?.detail || 'Failed to start indexing.');
      setIsIndexing(false);
    }
  }, []);

  useEffect(() => {
    let intervalId;

    const pollStatuses = async () => {
      // Опрос статуса конвертации
      if (isConverting && conversionTaskId) {
        try {
          const status = await ragApi.getConversionStatus(conversionTaskId);
          setConversionStatus(status);
          const currentStatus = status?.progress?.status;
          if (['completed', 'failed'].includes(currentStatus)) {
            setIsConverting(false);
            setConversionTaskId(null);
            // Если конвертация прошла успешно и были сконвертированы файлы, запускаем индексацию
            if (currentStatus === 'completed' && status.progress.converted_files > 0) {
              setTimeout(handleStartIndexing, 1000); // Небольшая задержка перед стартом
            }
          }
        } catch (err) {
          console.error('Conversion polling error:', err);
          setError('Failed to get conversion status.');
          setIsConverting(false);
        }
      }

      // Опрос статуса индексации
      if (isIndexing && indexingTaskId) {
        try {
          const status = await ragApi.getIndexingStatus(indexingTaskId);
          console.log('📊 Indexing Status received:', JSON.stringify(status, null, 2));
          setIndexingStatus(status);
          const currentStatus = status?.progress?.status;
          if (['completed', 'failed', 'cancelled'].includes(currentStatus)) {
            setIsIndexing(false);
            setIndexingTaskId(null);
            fetchDocumentStats(); // Обновляем статистику после завершения

            if (currentStatus === 'completed') {
                const processed = status.statistics?.documents_processed ?? 0;
                console.log('✅ INDEXING COMPLETED:', {
                  documents_processed: processed,
                  full_statistics: status.statistics,
                  raw_value: status.statistics?.documents_processed
                });
                setIndexingResult({ type: 'success', message: `Successfully indexed ${processed} new file(s).` });
            } else {
                setIndexingResult({ type: 'error', message: `Indexing failed. Check logs for details.` });
            }
          }
        } catch (err) {
          console.error('Indexing polling error:', err);
          setError('Failed to get indexing status.');
          setIsIndexing(false);
        }
      }
    };

    if (isConverting || isIndexing) {
      intervalId = setInterval(pollStatuses, 2000);
    }

    return () => clearInterval(intervalId);
  }, [isConverting, conversionTaskId, isIndexing, indexingTaskId, fetchDocumentStats, handleStartIndexing]);


  // --- EVENT HANDLERS ---

  const handleFilesSelected = async (files) => {
    if (files.length === 0) return;

    // Сброс всех состояний перед новой операцией
    setError(null);
    setConversionStatus(null);
    setIndexingStatus(null);
    setIndexingResult(null);
    setConversionTaskId(null);
    setIndexingTaskId(null);
    setUploadMessage(null); // Clear previous upload message
    setIsUploading(true);

    try {
      console.log(`Starting upload of ${files.length} files...`);

      let uploadedCount = 0;
      let duplicateCount = 0;
      let duplicateFiles = [];
      let failedFiles = [];

      for (const file of files) {
        try {
          const uploadResponse = await ragApi.uploadDocument(file, false); // false = не запускать индексацию автоматически

          // Check if file is duplicate
          if (uploadResponse.duplicate) {
            duplicateCount++;
            duplicateFiles.push(file.name);
            console.log(`📋 Duplicate file: ${file.name} (already indexed)`);
          } else {
            uploadedCount++;
          }
        } catch (uploadError) {
          // Handle individual file upload errors (e.g., file too large)
          const errorDetail = uploadError.response?.data?.detail || uploadError.message;
          failedFiles.push({ name: file.name, error: errorDetail });
          console.error(`❌ Failed to upload ${file.name}:`, errorDetail);
        }
      }

      console.log(`✅ Upload complete: ${uploadedCount} new, ${duplicateCount} duplicates, ${failedFiles.length} failed`);
      setIsUploading(false);

      // Show error message if some files failed to upload
      if (failedFiles.length > 0) {
        const failedMessage = failedFiles.length === 1
          ? `❌ Failed to upload "${failedFiles[0].name}": ${failedFiles[0].error}`
          : `❌ Failed to upload ${failedFiles.length} file(s): ${failedFiles.map(f => `${f.name} (${f.error})`).join(', ')}`;

        setUploadMessage({
          type: 'error',
          message: failedMessage
        });

        // If ALL files failed, stop here
        if (uploadedCount === 0 && duplicateCount === 0) {
          return;
        }
      }

      // Show message if all files were duplicates
      if (uploadedCount === 0 && duplicateCount > 0) {
        setUploadMessage({
          type: 'info',
          message: `✅ All ${duplicateCount} file(s) already exist in the system and have been indexed: ${duplicateFiles.join(', ')}`
        });
        return; // Don't start conversion/indexing
      }

      // Show info if some files were duplicates
      if (duplicateCount > 0 && failedFiles.length === 0) {
        setUploadMessage({
          type: 'warning',
          message: `⚠️ ${duplicateCount} duplicate file(s) skipped: ${duplicateFiles.join(', ')}`
        });
      }

      // Start conversion only if we have new files
      if (uploadedCount > 0) {
        setIsConverting(true);
        const response = await ragApi.startConversion(uploadSettings);
        setConversionTaskId(response.task_id);
      }

    } catch (err) {
      console.error('Failed to upload or convert:', err);
      setError(err.message || err.response?.data?.detail || 'Failed to process files.');
      setIsUploading(false);
      setIsConverting(false);
    }
  };

  const isOperationRunning = isUploading || isConverting || isIndexing;

  return (
    <div className="indexing-page">
      <div className="indexing-left-column">
        {/* Card: Document Upload & Conversion */}
        <div className="card">
          <div className="card-header">
            <h3>Document Upload & Conversion</h3>
          </div>
          <div className="card-body">
            <FileUploader
              onFilesSelected={handleFilesSelected}
              disabled={isOperationRunning}
              isUploading={isUploading}
              settings={uploadSettings}
              onSettingsChange={setUploadSettings}
            />

            {/* Upload Message */}
            {uploadMessage && (
              <div className={`upload-message ${uploadMessage.type}`} style={{
                marginTop: '1rem',
                padding: '1rem',
                borderRadius: '4px',
                backgroundColor: uploadMessage.type === 'info' ? '#e3f2fd' : uploadMessage.type === 'warning' ? '#fff3e0' : '#ffebee',
                border: uploadMessage.type === 'info' ? '1px solid #2196f3' : uploadMessage.type === 'warning' ? '1px solid #ff9800' : '1px solid #f44336',
                color: uploadMessage.type === 'info' ? '#1565c0' : uploadMessage.type === 'warning' ? '#e65100' : '#c62828'
              }}>
                {uploadMessage.message}
              </div>
            )}
          </div>
        </div>

        {/* Card: Conversion Progress */}
        {(isConverting || conversionStatus) && (
          <div className="card">
            <div className="card-header">
              <h3>Conversion Progress</h3>
            </div>
            <div className="card-body">
              <ConversionProgress status={conversionStatus} isActive={isConverting} />
            </div>
          </div>
        )}
      </div>

      <div className="indexing-right-column">
        {/* Card: Indexing Control */}
        <div className="card">
          <div className="card-header">
            <h3>Vector Indexing</h3>
          </div>
          <div className="card-body">
            <p>Process converted files into searchable vectors.</p>
            <div className="indexing-control-wrapper">
              <button
                className="start-indexing-button"
                onClick={handleStartIndexing}
                disabled={isOperationRunning}
              >
                {isIndexing && (
                  <span className="button-spinner">
                    <span className="spinner-dot"></span>
                    <span className="spinner-dot"></span>
                    <span className="spinner-dot"></span>
                  </span>
                )}
                {isIndexing ? 'Indexing...' : 'Start Manual Indexing'}
              </button>
            </div>
            {indexingResult && (
                <div className={`indexing-result ${indexingResult.type}`}>
                    {indexingResult.message}
                </div>
            )}
            {(isIndexing || indexingStatus) && (
              <IndexingProgress status={indexingStatus} isActive={isIndexing} />
            )}
          </div>
        </div>

        {/* Card: Indexing Statistics */}
        <div className="card">
          <div className="card-header">
            <h3>📈 Indexing Statistics</h3>
            <button className="refresh-button" onClick={fetchDocumentStats} disabled={loadingStats}>
              {loadingStats ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
          <div className="card-body">
            {loadingStats ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#6c757d' }}>
                Loading statistics...
              </div>
            ) : docStats ? (
              <div className="indexing-statistics">
                <div className="stats-summary">
                  <div className="stat-item-inline">
                    <span className="stat-label">Documents:</span>
                    <span className="stat-value">{(docStats.total_documents || 0).toLocaleString()}</span>
                  </div>
                  <div className="stat-separator">|</div>
                  <div className="stat-item-inline">
                    <span className="stat-label">Chunks:</span>
                    <span className="stat-value">{(docStats.total_chunks || 0).toLocaleString()}</span>
                  </div>
                  <div className="stat-separator">|</div>
                  <div className="stat-item-inline">
                    <span className="stat-label">Total size:</span>
                    <span className="stat-value">
                      {((docStats.total_characters || 0) / 1024 / 1024).toFixed(2)} MB
                    </span>
                  </div>
                </div>
                <button
                  className="manage-docs-button"
                  disabled
                  style={{
                    marginTop: '1.5rem',
                    padding: '0.75rem 1.5rem',
                    backgroundColor: '#e9ecef',
                    color: '#6c757d',
                    border: '1px solid #dee2e6',
                    borderRadius: '4px',
                    cursor: 'not-allowed',
                    fontSize: '1rem',
                    width: '100%',
                    textAlign: 'center'
                  }}
                  title="Document Manager page coming soon"
                >
                  Manage Documents → (Coming Soon)
                </button>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#dc3545' }}>
                Failed to load statistics
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default IndexingPage;