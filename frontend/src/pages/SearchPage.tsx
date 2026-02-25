import React, { useState } from 'react';
import { 
  Layout, Input, Card, Typography, Space, Tag, Empty, Spin, 
  message, Checkbox, Dropdown, Button, Tooltip, Menu
} from 'antd';
import { 
  SearchOutlined, ArrowLeftOutlined, FileTextOutlined, 
  EllipsisOutlined, DownloadOutlined, ThunderboltOutlined,
  DeleteOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

const { Header, Content, Sider } = Layout;
const { Text } = Typography;
const { Search } = Input;

interface SearchPaper {
  id: string;
  title: string;
  status: string;
  folder_id: string | null;
  created_at: string;
  score: number;
  snippets: string[];
}

const statusConfig: Record<string, { color: string; label: string }> = {
  indexed: { color: 'green', label: '已索引' },
  uploaded: { color: 'blue', label: '已上传' },
  processing: { color: 'processing', label: '处理中' },
  vectorizing: { color: 'processing', label: '向量化中' },
  error: { color: 'red', label: '失败' },
};

const getStatusDisplay = (status: string) => {
  const cfg = statusConfig[status] || { color: 'default', label: status };
  return <Tag color={cfg.color}>{cfg.label}</Tag>;
};

const formatDate = (dateStr: string) => {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return '刚刚';
  if (diffMins < 60) return `${diffMins} 分钟前`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours} 小时前`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays} 天前`;
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

const SearchPage: React.FC = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [papers, setPapers] = useState<SearchPaper[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [hoveredRow, setHoveredRow] = useState<string | null>(null);
  const [expandedSnippets, setExpandedSnippets] = useState<Set<string>>(new Set());

  const handleSearch = async (val: string) => {
    const q = val.trim();
    if (!q) { message.warning('请输入搜索内容'); return; }
    setLoading(true);
    setSearched(true);
    setQuery(q);
    try {
      const res = await api.post('/search/semantic', { query: q, top_k: 50 });
      setPapers(res.data.papers || []);
      setTotal(res.data.total || 0);
      if (res.data.message) message.info(res.data.message);
    } catch (err) {
      message.error('搜索失败');
      setPapers([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPaper = (paperId: string, title: string) => {
    const link = document.createElement('a');
    link.href = `/api/papers/${paperId}/view`;
    link.download = `${title}.pdf`;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const toggleSnippets = (paperId: string) => {
    const next = new Set(expandedSnippets);
    if (next.has(paperId)) next.delete(paperId);
    else next.add(paperId);
    setExpandedSnippets(next);
  };

  const getDropdownItems = (paper: SearchPaper) => ({
    items: [
      { key: 'open', label: '打开论文', onClick: () => window.open(`/papers/${paper.id}`, '_blank') },
      { key: 'download', label: '下载 PDF', icon: <DownloadOutlined />, onClick: () => handleDownloadPaper(paper.id, paper.title) },
      { key: 'vectorize', label: '向量化', icon: <ThunderboltOutlined />, onClick: async () => {
        try { await api.post('/batch/', { operation_type: 'vectorize', paper_ids: [paper.id] }); message.success('向量化任务已启动'); }
        catch { message.error('操作失败'); }
      }},
    ]
  });

  const getRowStyle = (id: string): React.CSSProperties => ({
    padding: '10px 16px',
    background: hoveredRow === id ? '#fafafa' : 'transparent',
    borderRadius: 6,
    marginBottom: 2,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    transition: 'background 0.15s',
    borderBottom: '1px solid #f0f0f0',
  });

  return (
    <Layout style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      {/* Header */}
      <Header style={{ background: '#fff', borderBottom: '1px solid #f0f0f0', display: 'flex', alignItems: 'center', padding: '0 24px' }}>
        <Space size="large" style={{ width: '100%' }}>
          <ArrowLeftOutlined onClick={() => navigate('/')} style={{ cursor: 'pointer', fontSize: 18 }} />
          <Search
            placeholder="输入关键词或一段描述，从所有已向量化论文中语义检索..."
            onSearch={handleSearch}
            enterButton="搜索"
            size="large"
            style={{ width: 680 }}
            loading={loading}
            allowClear
          />
        </Space>
      </Header>

      {/* Content */}
      <Content style={{ padding: '24px', maxWidth: 1100, margin: '0 auto', width: '100%' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '100px 0' }}>
            <Spin size="large" tip="正在从向量数据库中检索..." />
          </div>
        ) : !searched ? (
          <Card style={{ textAlign: 'center', padding: '60px 0', marginTop: 40 }}>
            <SearchOutlined style={{ fontSize: 48, color: '#d9d9d9', marginBottom: 16 }} />
            <div><Text type="secondary" style={{ fontSize: 16 }}>输入关键词或一段描述开始全文语义搜索</Text></div>
            <div style={{ marginTop: 8 }}><Text type="secondary">将从所有已向量化的论文中检索最相关的内容</Text></div>
          </Card>
        ) : papers.length === 0 ? (
          <Empty description="未找到相关论文" style={{ marginTop: 100 }} />
        ) : (
          <Card
            title={
              <Space>
                <span style={{ fontSize: 16, fontWeight: 600 }}>搜索结果</span>
                <Tag color="blue">共 {total} 篇相关论文</Tag>
              </Space>
            }
            bodyStyle={{ padding: '16px 0' }}
          >
            {/* Column header */}
            <div style={{ padding: '8px 24px', display: 'flex', alignItems: 'center', color: '#8c8c8c', fontSize: 12, fontWeight: 500, borderBottom: '1px solid #f0f0f0' }}>
              <span style={{ width: 28 }} />
              <span style={{ flex: 1 }}>论文名称</span>
              <span style={{ width: 70, textAlign: 'center' }}>相关度</span>
              <span style={{ width: 80, textAlign: 'center' }}>状态</span>
              <span style={{ width: 100, textAlign: 'center' }}>添加时间</span>
              <span style={{ width: 48, textAlign: 'center' }}>操作</span>
            </div>

            <div style={{ padding: '0 8px' }}>
              {papers.map((paper) => (
                <div key={paper.id}>
                  {/* Main row */}
                  <div
                    onClick={() => toggleSnippets(paper.id)}
                    onMouseEnter={() => setHoveredRow(paper.id)}
                    onMouseLeave={() => setHoveredRow(null)}
                    style={getRowStyle(paper.id)}
                  >
                    <FileTextOutlined style={{ fontSize: 18, color: '#1890ff', marginRight: 10 }} />
                    <Tooltip title={paper.title} mouseEnterDelay={0.5}>
                      <span
                        className="file-name-link"
                        style={{ flex: 1, fontWeight: 500, color: '#1890ff', cursor: 'pointer', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                        onClick={(e) => { e.stopPropagation(); window.open(`/papers/${paper.id}`, '_blank'); }}
                      >
                        {paper.title}
                      </span>
                    </Tooltip>
                    <span style={{ width: 70, textAlign: 'center' }}>
                      <Tag color={paper.score > 0.7 ? 'green' : paper.score > 0.4 ? 'orange' : 'default'} style={{ margin: 0 }}>
                        {(paper.score * 100).toFixed(0)}%
                      </Tag>
                    </span>
                    <span style={{ width: 80, textAlign: 'center' }}>
                      {getStatusDisplay(paper.status)}
                    </span>
                    <span style={{ width: 100, textAlign: 'center', color: '#8c8c8c', fontSize: 13 }}>
                      {formatDate(paper.created_at)}
                    </span>
                    <span style={{ width: 48, textAlign: 'center' }}>
                      <Dropdown menu={getDropdownItems(paper)} trigger={['click']}>
                        <Button type="text" size="small" icon={<EllipsisOutlined />} onClick={(e) => e.stopPropagation()} />
                      </Dropdown>
                    </span>
                  </div>

                  {/* Expandable snippets */}
                  {expandedSnippets.has(paper.id) && paper.snippets && paper.snippets.length > 0 && (
                    <div style={{ padding: '8px 24px 12px 52px', background: '#fafafa', borderBottom: '1px solid #f0f0f0', borderRadius: '0 0 6px 6px' }}>
                      <Text type="secondary" style={{ fontSize: 12, fontWeight: 500 }}>匹配片段：</Text>
                      {paper.snippets.map((snippet, idx) => (
                        <div key={idx} style={{ marginTop: 6, padding: '6px 10px', background: '#fff', borderRadius: 4, border: '1px solid #f0f0f0', fontSize: 13, color: '#555', lineHeight: 1.6 }}>
                          {snippet}...
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        )}
      </Content>
    </Layout>
  );
};

export default SearchPage;
