import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { Spin, Button, Space, Typography, Slider, Tooltip } from 'antd';
import { ZoomInOutlined, ZoomOutOutlined, LeftOutlined, RightOutlined, AppstoreOutlined, UnorderedListOutlined } from '@ant-design/icons';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

const { Text } = Typography;

interface PDFViewerProps {
  url: string;
}

const PDFViewer: React.FC<PDFViewerProps> = ({ url }) => {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.0);
  const [loading, setLoading] = useState<boolean>(true);
  const [containerWidth, setContainerWidth] = useState<number>(800);
  const [viewMode, setViewMode] = useState<'single' | 'continuous'>('single');
  const containerRef = useRef<HTMLDivElement>(null);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setLoading(false);
  };

  const onDocumentLoadError = (error: Error) => {
    console.error('PDF load error:', error);
    setLoading(false);
  };

  const goToPrevPage = () => setPageNumber(prev => Math.max(prev - 1, 1));
  const goToNextPage = () => setPageNumber(prev => Math.min(prev + 1, numPages));
  const zoomIn = () => setScale(prev => Math.min(prev + 0.2, 3.0));
  const zoomOut = () => setScale(prev => Math.max(prev - 0.2, 0.5));

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (viewMode === 'single') {
      if (e.key === 'ArrowLeft') goToPrevPage();
      if (e.key === 'ArrowRight') goToNextPage();
    }
    if (e.key === '+' || e.key === '=') zoomIn();
    if (e.key === '-') zoomOut();
  }, [numPages, viewMode]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.clientWidth - 40);
      }
    };
    updateWidth();
    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, []);

  const pageNumbers = viewMode === 'continuous' && numPages > 0 
    ? Array.from({ length: numPages }, (_, i) => i + 1) 
    : [pageNumber];

  return (
    <div
      ref={containerRef}
      style={{ height: '100%', overflow: 'auto', background: '#525659' }}
    >
      <div style={{ 
        position: 'sticky', 
        top: 0, 
        zIndex: 100, 
        background: '#fff', 
        padding: '8px 16px', 
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <Space>
          {viewMode === 'single' ? (
            <>
              <Button icon={<LeftOutlined />} onClick={goToPrevPage} disabled={pageNumber <= 1} />
              <Text>{pageNumber} / {numPages || '-'}</Text>
              <Button icon={<RightOutlined />} onClick={goToNextPage} disabled={pageNumber >= numPages} />
            </>
          ) : (
            <Text>共 {numPages || '-'} 页 (连续视图)</Text>
          )}
        </Space>
        <Space>
          <Tooltip title={viewMode === 'single' ? '切换到连续视图' : '切换到单页视图'}>
            <Button 
              icon={viewMode === 'single' ? <UnorderedListOutlined /> : <AppstoreOutlined />} 
              onClick={() => setViewMode(viewMode === 'single' ? 'continuous' : 'single')}
            />
          </Tooltip>
          <Button icon={<ZoomOutOutlined />} onClick={zoomOut} disabled={scale <= 0.5} />
          <Slider 
            value={scale} 
            min={0.5} 
            max={3.0} 
            step={0.1} 
            onChange={setScale}
            style={{ width: 100 }}
            tooltip={{ formatter: (v) => `${Math.round(v! * 100)}%` }}
          />
          <Button icon={<ZoomInOutlined />} onClick={zoomIn} disabled={scale >= 3.0} />
          <Text>{Math.round(scale * 100)}%</Text>
        </Space>
      </div>

      <div style={{ 
        display: 'flex', 
        flexDirection: 'column',
        alignItems: 'center', 
        padding: '20px 0', 
        minHeight: 'calc(100% - 56px)' 
      }}>
        {loading && (
          <div style={{ 
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)'
          }}>
            <Spin size="large" tip="加载 PDF..." />
          </div>
        )}
        <Document
          file={url}
          onLoadSuccess={onDocumentLoadSuccess}
          onLoadError={onDocumentLoadError}
          loading={null}
        >
          {pageNumbers.map((pageNum) => (
            <div 
              key={`page-${pageNum}`} 
              style={{ 
                marginBottom: viewMode === 'continuous' ? 16 : 0,
                position: 'relative'
              }}
            >
              <Page 
                pageNumber={pageNum} 
                scale={scale}
                width={containerWidth}
                renderTextLayer={true}
                renderAnnotationLayer={true}
              />
              {viewMode === 'continuous' && (
                <div style={{ 
                  textAlign: 'center', 
                  padding: '4px 0', 
                  background: '#f0f0f0', 
                  fontSize: 12, 
                  color: '#666' 
                }}>
                  {pageNum} / {numPages}
                </div>
              )}
            </div>
          ))}
        </Document>
      </div>
    </div>
  );
};

export default PDFViewer;
