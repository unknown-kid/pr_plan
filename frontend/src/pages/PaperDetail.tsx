import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout, Button, Input, List, Card, Space, Typography, message, Divider, Tabs, Empty, Spin, Progress, Alert, Tag, Modal, Select, Tooltip } from 'antd';
import { ArrowLeftOutlined, SendOutlined, RobotOutlined, CheckCircleOutlined, SyncOutlined, ExclamationCircleOutlined, PlusOutlined, RightOutlined, LeftOutlined, DeleteOutlined, MessageOutlined, ClockCircleOutlined, GlobalOutlined, FileTextOutlined, BookOutlined } from '@ant-design/icons';
import { paperService, chatService } from '../services/paperService';
import api from '../services/api';
import useUserStore from '../store/userStore';
import ReportViewer from '../components/paper/ReportViewer';
import SelectionTranslator from '../components/common/SelectionTranslator';
import PDFViewer from '../components/common/PDFViewer';
import MarkdownRenderer from '../components/common/MarkdownRenderer';

const { Header, Content, Sider } = Layout;
const { Title, Text } = Typography;

const PaperDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { token } = useUserStore();
  
  const [paper, setPaper] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  
  const [loading, setLoading] = useState(true);
  const [chatLoading, setChatLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  
  const [vectorizing, setVectorizing] = useState(false);
  const [chatHistoryKey, setChatHistoryKey] = useState(0);
  const [historyVisible, setHistoryVisible] = useState(false);
  const [sessions, setSessions] = useState<any[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [siderWidth, setSiderWidth] = useState(450);
  const [isResizing, setIsResizing] = useState(false);
  const [ragScope, setRagScope] = useState<'single' | 'all'>('single');
  const [availableReports, setAvailableReports] = useState<any[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<string | undefined>(undefined);
  
  const chatEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const fetchPaper = async () => {
    try {
      const res = await paperService.get(id!);
      setPaper(res.data);
      if (res.data.status === 'processing') {
        setVectorizing(true);
        startPollingVectorization();
      } else {
        setVectorizing(false);
      }
    } catch (err) {
      message.error('获取论文失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableReports = async () => {
    try {
      const res = await api.get('/reports/', { params: { paper_id: id } });
      const completed = res.data.filter((r: any) => r.status === 'completed');
      setAvailableReports(completed);
    } catch (err) {
      // Silently fail — reports are optional
    }
  };

  useEffect(() => {
    fetchPaper();
    fetchAvailableReports();
    setMessages([{ 
      role: 'assistant', 
      content: `你好！我是你的论文助手。我已经准备好和你讨论关于这篇论文的内容了。您可以问我摘要总结、核心观点或者具体细节。`,
      time: new Date()
    }]);
  }, [id]);

  useEffect(() => {
    if (paper) {
      document.title = paper.title;
    }
    return () => {
      document.title = 'Paper Reader';
    };
  }, [paper]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const startPollingVectorization = () => {
    const interval = setInterval(async () => {
      try {
        const res = await paperService.get(id!);
        setPaper(res.data);
        if (res.data.status === 'indexed') {
          setVectorizing(false);
          clearInterval(interval);
          message.success('论文向量化完成');
        } else if (res.data.status === 'error') {
          setVectorizing(false);
          clearInterval(interval);
          message.error('向量化失败，请通过“连通性测试”检查模型配置');
        }
      } catch (err) {
        clearInterval(interval);
      }
    }, 2000);
  };

  const handleManualVectorize = async () => {
    setVectorizing(true);
    try {
      await api.post('/batch/', {
        operation_type: 'vectorize',
        paper_ids: [id]
      });
      message.info('已启动向量化任务');
      startPollingVectorization();
    } catch (err) {
      setVectorizing(false);
      message.error('启动任务失败');
    }
  };

  const handleSendMessage = async (queryOverride?: string) => {
    const queryText = queryOverride || inputValue;
    if (!queryText.trim() || chatLoading || vectorizing || !paper) return;
    
    let currentSessionId = sessionId;
    if (!currentSessionId) {
      try {
        const res = await chatService.createSession(id);
        currentSessionId = res.data.id;
        setSessionId(currentSessionId);
      } catch (err) {
        message.error('创建会话失败，请检查 AI 模型配置');
        return;
      }
    }

    const now = new Date();
    const userMsg = { role: 'user', content: queryText, time: now };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInputValue('');
    setChatLoading(true);
    setIsTyping(true);

    try {
      // 直接从 localStorage 获取 token，避免新标签页中 store 状态延迟问题
      const currentToken = token || localStorage.getItem('token');
      console.log('[DEBUG] Token check - store:', !!token, 'localStorage:', !!localStorage.getItem('token'));
      
      if (!currentToken) {
        throw new Error('登录已过期，请重新登录');
      }
      
      console.log('[DEBUG] Starting fetch to:', `/api/conversations/${currentSessionId}/chat`);
      const requestBody = {
        query: userMsg.content,
        paper_id: id,
        rag_scope: ragScope,
        report_id: selectedReportId || undefined,
      };
      console.log('[DEBUG] Request body:', JSON.stringify(requestBody));
      
      const response = await fetch(`/api/conversations/${currentSessionId}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': '*/*',
          'Authorization': `Bearer ${currentToken}`
        },
        body: JSON.stringify(requestBody)
      });

      console.log('[DEBUG] Fetch response status:', response.status, 'ok:', response.ok);
      console.log('[DEBUG] Response headers:', Object.fromEntries(response.headers.entries()));

      if (!response.ok) {
        const errorText = await response.text();
        console.error('[DEBUG] Response error body:', errorText);
        throw new Error(`网络请求失败: ${response.status}`);
      }

      console.log('[DEBUG] Response body:', response.body);
      console.log('[DEBUG] Response body type:', response.body?.constructor?.name);
      console.log('[DEBUG] Response body locked:', response.body?.locked);
      
      if (!response.body) {
        throw new Error('响应体为空');
      }
      
      const reader = response.body.getReader();
      console.log('[DEBUG] Response body reader:', !!reader);
      
      if (!reader) {
        throw new Error('无法读取响应流');
      }
      
      const decoder = new TextDecoder();
      let done = false;
      let fullText = '';
      let chunkCount = 0;
      
      console.log('[DEBUG] Initializing assistant message');
      setMessages(prev => {
        console.log('[DEBUG] Current messages length before adding:', prev.length);
        return [...prev, { role: 'assistant', content: '', time: new Date() }];
      });
      setIsTyping(false);

      console.log('[DEBUG] Starting stream read loop');
      while (!done) {
        try {
          const { value, done: doneReading } = await reader.read();
          done = doneReading;
          chunkCount++;
          
          console.log(`[DEBUG] Chunk ${chunkCount} - done:`, done, 'hasValue:', !!value, 'valueLength:', value?.length || 0);
          
          if (value) {
            const chunkValue = decoder.decode(value, { stream: true });
            fullText += chunkValue;
            
            console.log(`[DEBUG] Chunk ${chunkCount} content length:`, chunkValue.length, 'total length:', fullText.length);
            console.log(`[DEBUG] Chunk ${chunkCount} preview:`, chunkValue.substring(0, 50));
            
            // 使用函数式更新避免闭包问题
            setMessages(prev => {
              const newMessages = [...prev];
              const lastIndex = newMessages.length - 1;
              console.log('[DEBUG] Updating message at index:', lastIndex, 'current role:', newMessages[lastIndex]?.role);
              if (lastIndex >= 0 && newMessages[lastIndex].role === 'assistant') {
                newMessages[lastIndex] = { 
                  ...newMessages[lastIndex], 
                  content: fullText 
                };
              }
              return newMessages;
            });
          }
        } catch (readErr: any) {
          console.error('[DEBUG] Read stream error:', readErr);
          console.error('[DEBUG] Error stack:', readErr.stack);
          throw new Error('读取响应流失败: ' + readErr.message);
        }
      }
      
      console.log('[DEBUG] Stream read complete - total chunks:', chunkCount, 'final text length:', fullText.length);
    } catch (err: any) {
      console.error('[DEBUG] Chat error caught:', err);
      console.error('[DEBUG] Error type:', err.constructor.name);
      console.error('[DEBUG] Error message:', err.message);
      console.error('[DEBUG] Error stack:', err.stack);
      message.error(err.message || '对话失败');
      setMessages(prev => [...prev, { role: 'assistant', content: `❌ 错误: ${err.message}`, time: new Date() }]);
    } finally {
      console.log('[DEBUG] Chat finally block - cleaning up states');
      setChatLoading(false);
      setIsTyping(false);
      setChatHistoryKey(prev => prev + 1);
    }
  };

  const handleAskAI = (selectedText: string, question: string) => {
    const fullQuery = question 
      ? `关于论文中的这段内容：\n\n"${selectedText}"\n\n${question}`
      : `请解释论文中的这段内容：\n\n"${selectedText}"`;
    handleSendMessage(fullQuery);
  };

  const handleSelectSession = (newSessionId: string, sessionMessages: any[]) => {
    setSessionId(newSessionId);
    if (sessionMessages && sessionMessages.length > 0) {
      setMessages(sessionMessages.map((m: any) => ({ 
        role: m.role, 
        content: m.content,
        time: m.created_at ? new Date(m.created_at) : new Date()
      })));
    } else {
      setMessages([{ 
        role: 'assistant', 
        content: `你好！我是你的论文助手。我已经准备好和你讨论关于这篇论文的内容了。您可以问我摘要总结、核心观点或者具体细节。`,
        time: new Date()
      }]);
    }
  };

  const handleNewSession = () => {
    setSessionId(null);
    setMessages([{ 
      role: 'assistant', 
      content: `你好！我是你的论文助手。我已经准备好和你讨论关于这篇论文的内容了。您可以问我摘要总结、核心观点或者具体细节。`,
      time: new Date()
    }]);
  };

  const fetchSessions = async () => {
    setSessionsLoading(true);
    try {
      const res = await api.get(`/conversations/`, { params: { paper_id: id } });
      setSessions(res.data);
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    } finally {
      setSessionsLoading(false);
    }
  };

  const handleSelectSessionFromHistory = async (selectedSessionId: string) => {
    try {
      const res = await api.get(`/conversations/${selectedSessionId}/messages`);
      handleSelectSession(selectedSessionId, res.data.messages);
      setHistoryVisible(false);
    } catch (err) {
      message.error('加载会话失败');
    }
  };

  const handleDeleteSession = async (sessionIdToDelete: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.delete(`/conversations/${sessionIdToDelete}`);
      setSessions(sessions.filter((s) => s.id !== sessionIdToDelete));
      if (sessionId === sessionIdToDelete) {
        handleNewSession();
      }
      message.success('会话已删除');
    } catch (err) {
      message.error('删除失败');
    }
  };

  const handleDeletePaper = () => {
    Modal.confirm({
      title: '确认删除论文',
      content: `确定要删除论文「${paper?.title}」吗？此操作将删除论文的所有数据，包括对话历史、阅读进度等，且不可撤销。`,
      okText: '确认删除',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        try {
          await api.delete(`/papers/${id}/permanent`);
          message.success('论文已删除');
          if (window.opener) {
            window.close();
          } else {
            navigate('/');
          }
        } catch (err) {
          message.error('删除失败');
        }
      }
    });
  };

  useEffect(() => {
    if (id && historyVisible) {
      fetchSessions();
    }
  }, [id, historyVisible, chatHistoryKey]);

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    const isYesterday = date.toDateString() === yesterday.toDateString();
    
    const timeStr = date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false });
    
    if (isToday) {
      return `今天 ${timeStr}`;
    }
    if (isYesterday) {
      return `昨天 ${timeStr}`;
    }
    return date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' }) + ' ' + timeStr;
  };

  const formatMessageTime = (date: Date) => {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false });
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const containerRect = containerRef.current?.getBoundingClientRect();
      if (!containerRect) return;
      const newWidth = containerRect.right - e.clientX;
      if (newWidth >= 300 && newWidth <= 800) {
        setSiderWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isResizing]);

  const vecProgress = paper?.total_chunks > 0 
    ? Math.round((paper?.processed_chunks / paper?.total_chunks) * 100) 
    : 0;

  if (loading) {
    return (
      <Layout style={{ height: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <Spin size="large" tip="加载中..." />
      </Layout>
    );
  }

  if (!paper) {
    return (
      <Layout style={{ height: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <Empty description="论文不存在或已删除">
          <Button type="primary" onClick={() => navigate('/')}>返回首页</Button>
        </Empty>
      </Layout>
    );
  }

  return (
    <Layout style={{ height: '100vh', position: 'relative' }}>
      <SelectionTranslator onAskAI={handleAskAI} />
      
      {/* Prominent Progress Bar at the Top - Using Real Chunk Counts */}
      {vectorizing && (
        <div style={{ 
          position: 'fixed', 
          top: 0, 
          left: 0, 
          right: 0, 
          zIndex: 9999, 
          background: '#e6f7ff', 
          padding: '12px 24px', 
          borderBottom: '2px solid #1890ff',
          boxShadow: '0 4px 12px rgba(24, 144, 255, 0.2)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px', maxWidth: '1200px', margin: '0 auto' }}>
            <SyncOutlined spin style={{ color: '#1890ff', fontSize: '24px' }} />
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <Text strong style={{ color: '#0050b3', fontSize: '14px' }}>
                  正在解析论文分块并构建索引... 
                  {paper?.total_chunks > 0 && <span style={{ marginLeft: 8 }}>(进度: {paper.processed_chunks} / {paper.total_chunks} 块)</span>}
                </Text>
                <Text strong style={{ color: '#1890ff' }}>{vecProgress}%</Text>
              </div>
              <Progress percent={vecProgress} status="active" strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }} showInfo={false} strokeWidth={12} />
            </div>
          </div>
        </div>
      )}

      <Header style={{ 
        background: '#fff', 
        display: 'flex', 
        alignItems: 'center', 
        borderBottom: '1px solid #f0f0f0', 
        padding: '0 16px', 
        justifyContent: 'space-between', 
        marginTop: vectorizing ? '70px' : 0,
        transition: 'margin-top 0.3s cubic-bezier(0.645, 0.045, 0.355, 1)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', flex: 1, minWidth: 0 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')} style={{ marginRight: 16 }} />
          <Title level={4} style={{ margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{paper.title}</Title>
        </div>
        <Space>
          {paper.status === 'indexed' ? (
            <Tag color="success" icon={<CheckCircleOutlined />} style={{ fontSize: '14px', padding: '4px 12px' }}>已向量化</Tag>
          ) : paper.status === 'error' ? (
            <Tag color="error" icon={<ExclamationCircleOutlined />} style={{ fontSize: '14px', padding: '4px 12px' }}>向量化失败</Tag>
          ) : (
            <Tag color="processing" icon={<SyncOutlined spin />} style={{ fontSize: '14px', padding: '4px 12px' }}>处理中</Tag>
          )}
          <Button danger icon={<DeleteOutlined />} onClick={handleDeletePaper}>删除论文</Button>
        </Space>
      </Header>
      
      <Layout ref={containerRef} style={{ height: 'calc(100vh - 64px)', marginTop: vectorizing ? '70px' : 0, position: 'relative' }}>
        <Content style={{ background: '#f0f2f5', padding: 0, height: '100%', width: `calc(100% - ${siderWidth}px)` }}>
          <PDFViewer url={`/api/papers/${id}/view`} />
        </Content>
        <div
          onMouseDown={handleMouseDown}
          style={{
            position: 'absolute',
            right: siderWidth,
            top: 0,
            bottom: 0,
            width: 5,
            background: isResizing ? '#1890ff' : '#f0f0f0',
            cursor: 'col-resize',
            zIndex: 100,
            transition: isResizing ? 'none' : 'background 0.2s',
          }}
          onMouseEnter={(e) => {
            if (!isResizing) e.currentTarget.style.background = '#1890ff';
          }}
          onMouseLeave={(e) => {
            if (!isResizing) e.currentTarget.style.background = '#f0f0f0';
          }}
        />
        <Sider width={siderWidth} theme="light" style={{ borderLeft: '1px solid #f0f0f0' }}>
          <div style={{ height: '100%', padding: '16px' }}>
<Tabs defaultActiveKey="1" onChange={(key) => { if (key === '1') fetchAvailableReports(); }} style={{ height: '100%' }} items={[
              {
                key: '1',
                label: <span><RobotOutlined /> AI 助手</span>,
                children: (
                  <div style={{ display: 'flex', height: 'calc(100vh - 180px)', position: 'relative' }}>
                    <div style={{ 
                      flex: 1, 
                      display: 'flex', 
                      flexDirection: 'column',
                      marginRight: historyVisible ? 200 : 0,
                      transition: 'margin-right 0.3s'
                    }}>
                      <div style={{ 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        alignItems: 'center', 
                        padding: '4px 8px', 
                        borderBottom: '1px solid #f0f0f0', 
                        marginBottom: 8 
                      }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {sessionId ? '当前会话' : '新会话'}
                        </Text>
                        <Space>
                          {sessionId && (
                            <Button 
                              type="link" 
                              size="small" 
                              icon={<PlusOutlined />} 
                              onClick={handleNewSession}
                            >
                              新对话
                            </Button>
                          )}
                        </Space>
                      </div>
                      <div style={{ flex: 1, overflowY: 'auto', marginBottom: '16px', padding: '8px' }}>
                        <List
                          dataSource={messages}
                          renderItem={(item, index) => {
                            console.log(`[DEBUG] Rendering message ${index}:`, {
                              role: item.role,
                              contentLength: item.content?.length || 0,
                              contentPreview: item.content?.substring(0, 30),
                              hasTime: !!item.time
                            });
                            return (
                              <List.Item style={{ border: 'none', padding: '8px 0' }}>
                                <Card 
                                  size="small" 
                                  style={{ 
                                    width: '100%', 
                                    background: item.role === 'user' ? '#e6f7ff' : '#f6ffed',
                                    borderRadius: '8px',
                                    border: '1px solid #d9d9d9'
                                  }}
                                >
                                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                                    <Text strong>{item.role === 'user' ? '你' : 'AI'}</Text>
                                    {item.time && (
                                      <Text type="secondary" style={{ fontSize: 11 }}>
                                        {formatMessageTime(item.time instanceof Date ? item.time : new Date(item.time))}
                                      </Text>
                                    )}
                                  </div>
                                  {item.role === 'user' ? (
                                    <div style={{ whiteSpace: 'pre-wrap' }}>{item.content}</div>
                                  ) : (
                                    <MarkdownRenderer content={item.content || ''} />
                                  )}
                                </Card>
                              </List.Item>
                            );
                          }}
                        />
                        {isTyping && (
                          <div style={{ padding: '8px 0' }}>
                            <Card size="small" style={{ width: 'fit-content', background: '#f6ffed', borderRadius: '8px' }}>
                              <Space><Spin size="small" /><Text type="secondary">AI 正在思考中...</Text></Space>
                            </Card>
                          </div>
                        )}
                        <div ref={chatEndRef} />
                      </div>
                      
                      {paper.status === 'error' && !vectorizing && (
                        <Alert
                          message="向量化失败"
                          description="请在'模型配置'中通过'连通性测试'验证 API 后重试。"
                          type="error"
                          showIcon
                          action={<Button size="small" type="primary" danger onClick={handleManualVectorize}>重试向量化</Button>}
                          style={{ marginBottom: 16 }}
                        />
                      )}
                      
                      {paper.status !== 'indexed' && paper.status !== 'error' && !vectorizing && (
                        <Alert
                          message="论文未向量化"
                          description="向量化后 AI 助手能根据论文全文回答问题。"
                          type="warning"
                          showIcon
                          action={<Button size="small" type="primary" onClick={handleManualVectorize}>立即开始</Button>}
                          style={{ marginBottom: 16 }}
                        />
                      )}
                      
                      <div style={{ padding: '6px 8px', background: '#fafafa', borderTop: '1px solid #f0f0f0', display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Text type="secondary" style={{ fontSize: 12, marginRight: 4 }}>检索范围：</Text>
                        <Button
                          size="small"
                          type={ragScope === 'single' ? 'primary' : 'default'}
                          icon={<FileTextOutlined />}
                          onClick={() => setRagScope('single')}
                          style={{ fontSize: 12 }}
                        >
                          本论文
                        </Button>
                        <Button
                          size="small"
                          type={ragScope === 'all' ? 'primary' : 'default'}
                          icon={<GlobalOutlined />}
                          onClick={() => setRagScope('all')}
                          style={{ fontSize: 12 }}
                        >
                          全部论文
                        </Button>
                      </div>
                      <div style={{ padding: '4px 8px', background: '#fafafa', display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Tooltip title="将阅读报告作为对话上下文，AI 会参考报告内容回答问题">
                          <Text type="secondary" style={{ fontSize: 12, marginRight: 4, whiteSpace: 'nowrap' }}>
                            <BookOutlined style={{ marginRight: 2 }} />引用报告：
                          </Text>
                        </Tooltip>
                        <Select
                          size="small"
                          value={selectedReportId || 'none'}
                          onChange={(val) => setSelectedReportId(val === 'none' ? undefined : val)}
                          style={{ flex: 1, fontSize: 12 }}
                          options={[
                            { label: '不引用', value: 'none' },
                            ...availableReports.map((r: any) => ({
                              label: `v${r.version}${r.focus_directions ? ' - ' + r.focus_directions.substring(0, 15) + (r.focus_directions.length > 15 ? '...' : '') : ''} (${new Date(r.created_at).toLocaleDateString('zh-CN')})`,
                              value: r.id,
                            })),
                          ]}
                        />
                      </div>
                      <div style={{ display: 'flex', gap: '8px', padding: '8px', background: '#fff' }}>
                        <Input.TextArea 
                          value={inputValue} 
                          onChange={(e) => setInputValue(e.target.value)}
                          onPressEnter={(e) => {
                            if (!e.shiftKey) {
                              e.preventDefault();
                              handleSendMessage();
                            }
                          }}
                          autoSize={{ minRows: 1, maxRows: 4 }}
                          placeholder={ragScope === 'single' ? '基于本论文提问 (Shift+Enter 换行)...' : '基于全部论文提问 (Shift+Enter 换行)...'}
                          disabled={chatLoading || vectorizing}
                        />
                        <Button 
                          type="primary" 
                          icon={<SendOutlined />} 
                          onClick={() => handleSendMessage()} 
                          loading={chatLoading}
                          disabled={vectorizing}
                          style={{ height: 'auto' }}
                        />
                      </div>
                    </div>
                    
                    <div
                      onClick={() => setHistoryVisible(!historyVisible)}
                      style={{
                        position: 'absolute',
                        right: historyVisible ? 200 : 0,
                        top: '50%',
                        transform: 'translateY(-50%)',
                        width: 20,
                        height: 60,
                        background: '#f0f0f0',
                        borderRadius: historyVisible ? '4px 0 0 4px' : '0 4px 4px 0',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                        zIndex: 10,
                        transition: 'right 0.3s',
                      }}
                    >
                      {historyVisible ? <RightOutlined /> : <LeftOutlined />}
                    </div>
                    
                    <div
                      style={{
                        position: 'absolute',
                        right: 0,
                        top: 0,
                        bottom: 0,
                        width: 200,
                        background: '#fafafa',
                        borderLeft: '1px solid #f0f0f0',
                        display: historyVisible ? 'block' : 'none',
                        overflowY: 'auto',
                      }}
                    >
                      <div style={{ 
                        padding: '8px 12px', 
                        borderBottom: '1px solid #f0f0f0', 
                        background: '#fff',
                        position: 'sticky',
                        top: 0,
                        zIndex: 1
                      }}>
                        <Text strong style={{ fontSize: 13 }}>历史记录</Text>
                      </div>
                      {sessionsLoading ? (
                        <div style={{ textAlign: 'center', padding: '20px 0' }}>
                          <Spin size="small" />
                        </div>
                      ) : sessions.length === 0 ? (
                        <Empty
                          image={Empty.PRESENTED_IMAGE_SIMPLE}
                          description="暂无记录"
                          style={{ padding: '20px 0' }}
                        />
                      ) : (
                        <List
                          dataSource={sessions}
                          renderItem={(session) => (
                            <div
                              onClick={() => handleSelectSessionFromHistory(session.id)}
                              style={{
                                padding: '8px 12px',
                                cursor: 'pointer',
                                background: sessionId === session.id ? '#e6f7ff' : 'transparent',
                                borderBottom: '1px solid #f0f0f0',
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Space size={4}>
                                  <MessageOutlined style={{ color: '#1890ff', fontSize: 12 }} />
                                  <Text
                                    ellipsis
                                    style={{ maxWidth: 120, fontSize: 12 }}
                                    strong={sessionId === session.id}
                                  >
                                    {session.title || '未命名会话'}
                                  </Text>
                                </Space>
                                <Button
                                  type="text"
                                  size="small"
                                  icon={<DeleteOutlined style={{ color: '#999', fontSize: 12 }} />}
                                  onClick={(e) => handleDeleteSession(session.id, e)}
                                  style={{ padding: '0 4px', height: 18 }}
                                />
                              </div>
                              <div style={{ marginTop: 4 }}>
                                <Text type="secondary" style={{ fontSize: 11 }}>
                                  <ClockCircleOutlined style={{ marginRight: 4 }} />
                                  {formatTime(session.updated_at)}
                                </Text>
                              </div>
                            </div>
                          )}
                        />
                      )}
                    </div>
                  </div>
                )
              },
              {
                key: '2',
                label: '阅读报告',
                children: <ReportViewer paperId={id!} />
              },
              {
                key: '3',
                label: '笔记',
                children: <div style={{ padding: 24 }}><Empty description="笔记功能即将上线" /></div>
              }
            ]} />
          </div>
        </Sider>
      </Layout>
    </Layout>
  );
};

export default PaperDetail;
