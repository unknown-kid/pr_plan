import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Button, Card, Typography, Spin, message, Space, Input, Divider } from 'antd';
import { TranslationOutlined, CloseOutlined, DragOutlined, RobotOutlined, SendOutlined } from '@ant-design/icons';
import api from '../../services/api';

const { Text } = Typography;
const { TextArea } = Input;

interface SelectionTranslatorProps {
  onAskAI?: (selectedText: string, question: string) => void;
}

const SelectionTranslator: React.FC<SelectionTranslatorProps> = ({ onAskAI }) => {
  const [visible, setVisible] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [selectedText, setSelectedText] = useState('');
  const [translation, setTranslation] = useState('');
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [showAskAI, setShowAskAI] = useState(false);
  const [aiQuestion, setAiQuestion] = useState('');
  const dragStartPosRef = useRef({ x: 0, y: 0 });
  const popupStartPosRef = useRef({ x: 0, y: 0 });

  const handleTranslate = useCallback(async () => {
    if (!selectedText) return;
    setLoading(true);
    try {
      const res = await api.post('/translate/', { text: selectedText });
      setTranslation(res.data.translated_text);
    } catch (err: any) {
      message.error(err.response?.data?.detail || '翻译失败');
    } finally {
      setLoading(false);
    }
  }, [selectedText]);

  const handleClose = useCallback(() => {
    setVisible(false);
    setTranslation('');
    setSelectedText('');
    setShowAskAI(false);
    setAiQuestion('');
  }, []);

  const handleDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(true);
    dragStartPosRef.current = { x: e.clientX, y: e.clientY };
    popupStartPosRef.current = { ...position };
  }, [position]);

  const handleDragMove = useCallback((e: MouseEvent) => {
    if (!dragging) return;
    const deltaX = e.clientX - dragStartPosRef.current.x;
    const deltaY = e.clientY - dragStartPosRef.current.y;
    setPosition({
      x: popupStartPosRef.current.x + deltaX,
      y: popupStartPosRef.current.y + deltaY
    });
  }, [dragging]);

  const handleDragEnd = useCallback(() => {
    setDragging(false);
  }, []);

  const handleAskAI = useCallback(() => {
    if (onAskAI && selectedText) {
      onAskAI(selectedText, aiQuestion);
      handleClose();
    }
  }, [onAskAI, selectedText, aiQuestion, handleClose]);

  useEffect(() => {
    if (dragging) {
      document.addEventListener('mousemove', handleDragMove);
      document.addEventListener('mouseup', handleDragEnd);
      return () => {
        document.removeEventListener('mousemove', handleDragMove);
        document.removeEventListener('mouseup', handleDragEnd);
      };
    }
  }, [dragging, handleDragMove, handleDragEnd]);

  useEffect(() => {
    const handleSelectionMouseUp = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (target.closest('.selection-translator-popup')) {
        return;
      }

      const selection = window.getSelection();
      const text = selection?.toString().trim();
      
      if (text && text.length > 1) {
        setSelectedText(text);
        setPosition({ x: e.clientX, y: e.clientY });
        setTranslation('');
        setShowAskAI(false);
        setAiQuestion('');
        setVisible(true);
      } else if (!target.closest('.selection-translator-popup')) {
        setVisible(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleClose();
      }
    };

    document.addEventListener('mouseup', handleSelectionMouseUp);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mouseup', handleSelectionMouseUp);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleClose]);

  useEffect(() => {
    if (visible && selectedText && !translation && !loading) {
      handleTranslate();
    }
  }, [visible, selectedText, translation, loading, handleTranslate]);

  if (!visible) return null;

  return (
    <div 
      className="selection-translator-popup"
      style={{ 
        position: 'fixed', 
        left: position.x, 
        top: position.y + 10, 
        zIndex: 9999,
        transform: 'translateX(-50%)',
        userSelect: 'none',
      }}
    >
      <Card 
        size="small" 
        style={{ 
          width: 380, 
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          borderRadius: 8,
          maxHeight: '80vh',
          overflowY: 'auto',
        }} 
        bodyStyle={{ padding: 0 }}
      >
        <div 
          className="drag-handle"
          style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            padding: '8px 12px', 
            borderBottom: '1px solid #f0f0f0', 
            background: '#fafafa', 
            cursor: 'move', 
          }}
          onMouseDown={handleDragStart}
        >
          <Space>
            <DragOutlined style={{ color: '#999' }} />
            <Text strong style={{ fontSize: 12 }}>划词翻译</Text>
          </Space>
          <Button 
            type="text" 
            size="small" 
            icon={<CloseOutlined />} 
            onClick={handleClose}
            style={{ padding: 0, height: 20, width: 20 }}
          />
        </div>
        
        <div style={{ padding: '8px 12px' }}>
          <div style={{ 
            background: '#f5f5f5', 
            padding: 8, 
            borderRadius: 4, 
            marginBottom: 8,
            maxHeight: 80,
            overflowY: 'auto'
          }}>
            <Text style={{ fontSize: 12, color: '#666', wordBreak: 'break-all' }}>{selectedText}</Text>
          </div>
          
          {loading ? (
            <div style={{ textAlign: 'center', padding: '12px 0' }}>
              <Spin size="small" />
            </div>
          ) : (
            <div style={{ 
              background: '#e6f7ff', 
              padding: 8, 
              borderRadius: 4,
              marginBottom: 8,
              maxHeight: 200,
              overflowY: 'auto'
            }}>
              <Text style={{ fontSize: 13, wordBreak: 'break-all' }}>{translation}</Text>
            </div>
          )}

          {onAskAI && (
            <>
              <Divider style={{ margin: '8px 0' }} />
              
              {showAskAI ? (
                <div>
                  <TextArea
                    value={aiQuestion}
                    onChange={(e) => setAiQuestion(e.target.value)}
                    placeholder="输入你的问题..."
                    autoSize={{ minRows: 2, maxRows: 4 }}
                    style={{ marginBottom: 8, fontSize: 12 }}
                  />
                  <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                    <Button size="small" onClick={() => setShowAskAI(false)}>取消</Button>
                    <Button 
                      type="primary" 
                      size="small" 
                      icon={<SendOutlined />}
                      onClick={handleAskAI}
                    >
                      发送给AI
                    </Button>
                  </Space>
                </div>
              ) : (
                <Button 
                  type="default" 
                  size="small" 
                  icon={<RobotOutlined />} 
                  onClick={() => setShowAskAI(true)}
                  block
                  style={{ color: '#1890ff', borderColor: '#1890ff' }}
                >
                  问AI
                </Button>
              )}
            </>
          )}
        </div>
      </Card>
    </div>
  );
};

export default SelectionTranslator;
