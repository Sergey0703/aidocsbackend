// src/pages/IndexingPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import './IndexingPage.css';
import { ragApi } from '../api/ragApi';
import FileUploader from '../components/indexing/FileUploader';
import ConversionProgress from '../components/indexing/ConversionProgress';
import IndexingProgress from '../components/indexing/IndexingProgress';
import DocumentsList from '../components/indexing/DocumentsList';

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

  // Состояния для списка документов
  const [documents, setDocuments] = useState([]);
  const [loadingDocs, setLoadingDocs] = useState(true);

  // Настройки для загрузки и индексации
  const [uploadSettings, setUploadSettings] = useState({
    incremental: true,
    enableOcr: true,
    maxFileSizeMb: 50,
  });

  // Сообщения для пользователя
  const [error, setError] = useState(null);
  const [indexingResult, setIndexingResult] = useState(null);

  // --- DATA FETCHING ---

  const fetchDocuments = useCallback(async () => {
    setLoadingDocs(true);
    try {
      const data = await ragApi.listDocuments({ limit: 1000, sort_by: 'indexed_at', order: 'desc' });
      setDocuments(data.documents || []);
    } catch (err) {
      console.error("Failed to fetch documents:", err);
      setError("Could not load the list of indexed documents.");
    } finally {
      setLoadingDocs(false);
    }
  }, []);

  // Первоначальная загрузка списка документов
  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);


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
          setIndexingStatus(status);
          const currentStatus = status?.progress?.status;
          if (['completed', 'failed', 'cancelled'].includes(currentStatus)) {
            setIsIndexing(false);
            setIndexingTaskId(null);
            fetchDocuments(); // Обновляем список документов после завершения
            
            if (currentStatus === 'completed') {
                const processed = status.statistics?.documents_processed ?? 0;
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
  }, [isConverting, conversionTaskId, isIndexing, indexingTaskId, fetchDocuments, handleStartIndexing]);


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
    setIsUploading(true);

    try {
      console.log(`Starting upload of ${files.length} files...`);
      for (const file of files) {
        await ragApi.uploadDocument(file, false); // false = не запускать индексацию автоматически
      }
      
      console.log('✅ All files uploaded successfully!');
      setIsUploading(false);
      
      // Запускаем конвертацию после успешной загрузки
      setIsConverting(true);
      const response = await ragApi.startConversion(uploadSettings);
      setConversionTaskId(response.task_id);
      
    } catch (err) {
      console.error('Failed to upload or convert:', err);
      setError(err.message || err.response?.data?.detail || 'Failed to process files.');
      setIsUploading(false);
      setIsConverting(false);
    }
  };
  
  const handleDeleteDocument = async (filename) => {
    try {
      await ragApi.deleteDocument(filename);
      // Оптимистичное обновление UI для лучшего UX
      setDocuments(prev => prev.filter(doc => doc.filename !== filename));
    } catch (error) {
      console.error("Failed to delete document:", error);
      setError("Failed to delete the document.");
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
              settings={uploadSettings}
              onSettingsChange={setUploadSettings}
            />
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
            <button
              className="start-indexing-button"
              onClick={handleStartIndexing}
              disabled={isOperationRunning}
            >
              {isIndexing ? 'Indexing...' : 'Start Manual Indexing'}
            </button>
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

        {/* Card: Indexed Documents */}
        <div className="card">
          <div className="card-header">
            <h3>Indexed Documents</h3>
            <button className="refresh-button" onClick={fetchDocuments} disabled={loadingDocs}>
              {loadingDocs ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
          <div className="card-body">
            <DocumentsList
              documents={documents}
              loading={loadingDocs}
              onDelete={handleDeleteDocument}
              onRefresh={fetchDocuments}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default IndexingPage;