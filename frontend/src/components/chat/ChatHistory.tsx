import React, { useState, useEffect } from 'react';
import { List, Typography, Space, Button, Empty, Spin, Popconfirm, message } from 'antd';
import { MessageOutlined, DeleteOutlined, ClockCircleOutlined } from '@ant-design/icons';
import api from '../../services/api';

const { Text } = Typography;

interface Session {
  id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

interface ChatHistoryProps {
  paperId: string;
  currentSessionId: string | null;
  onSelectSession: (sessionId: string, messages: any[]) => void;
  onNewSession: () => void;
}

const ChatHistory: React.FC<ChatHistoryProps> = ({
  paperId,
  currentSessionId,
  onSelectSession,
  onNewSession,
}) => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchSessions = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/conversations/`, { params: { paper_id: paperId } });
      setSessions(res.data);
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (paperId) {
      fetchSessions();
    }
  }, [paperId]);

  const handleSelectSession = async (sessionId: string) => {
    try {
      const res = await api.get(`/conversations/${sessionId}/messages`);
      onSelectSession(sessionId, res.data.messages);
    } catch (err) {
      message.error('加载会话失败');
    }
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.delete(`/conversations/${sessionId}`);
      setSessions(sessions.filter((s) => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        onNewSession();
      }
      message.success('会话已删除');
    } catch (err) {
      message.error('删除失败');
    }
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return '刚刚';
    if (diffMins < 60) return `${diffMins}分钟前`;
    if (diffHours < 24) return `${diffHours}小时前`;
    if (diffDays < 7) return `${diffDays}天前`;
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '20px 0' }}>
        <Spin size="small" />
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="暂无聊天记录"
        style={{ padding: '20px 0' }}
      />
    );
  }

  return (
    <List
      dataSource={sessions}
      renderItem={(session) => (
        <List.Item
          onClick={() => handleSelectSession(session.id)}
          style={{
            cursor: 'pointer',
            padding: '8px 12px',
            background: currentSessionId === session.id ? '#e6f7ff' : 'transparent',
            borderRadius: 4,
            marginBottom: 4,
          }}
        >
          <div style={{ width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Space>
                <MessageOutlined style={{ color: '#1890ff' }} />
                <Text
                  ellipsis
                  style={{ maxWidth: 180, fontSize: 13 }}
                  strong={currentSessionId === session.id}
                >
                  {session.title}
                </Text>
              </Space>
              <Popconfirm
                title="确定删除此会话？"
                onConfirm={(e) => handleDeleteSession(session.id, e as any)}
                onCancel={(e) => e?.stopPropagation()}
              >
                <Button
                  type="text"
                  size="small"
                  icon={<DeleteOutlined style={{ color: '#999' }} />}
                  onClick={(e) => e.stopPropagation()}
                  style={{ padding: '0 4px' }}
                />
              </Popconfirm>
            </div>
            <div style={{ marginTop: 4 }}>
              <Space size={8}>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  <ClockCircleOutlined style={{ marginRight: 4 }} />
                  {formatTime(session.updated_at)}
                </Text>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {session.message_count} 条消息
                </Text>
              </Space>
            </div>
          </div>
        </List.Item>
      )}
    />
  );
};

export default ChatHistory;
