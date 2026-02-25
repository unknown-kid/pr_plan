import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Card, Button, Typography, Space, Tag, Empty, Spin, message, Alert, Popconfirm, Modal, Input } from 'antd';
import { FileTextOutlined, ReloadOutlined, DeleteOutlined, ClockCircleOutlined, EditOutlined, AimOutlined, DownloadOutlined } from '@ant-design/icons';
import api from '../../services/api';
import MarkdownRenderer from '../common/MarkdownRenderer';
import mermaid from 'mermaid';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

// Initialize mermaid
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  flowchart: { useMaxWidth: true, htmlLabels: true },
});

interface ReportViewerProps {
  paperId: string;
}

interface Report {
  id: string;
  title: string;
  content: string;
  version: number;
  status: string;
  error_message?: string;
  generation_time?: number;
  focus_directions?: string;
  created_at: string;
}

const MermaidChart: React.FC<{ chart: string }> = ({ chart }) => {
  const [svg, setSvg] = useState<string>('');
  const [error, setError] = useState<boolean>(false);
  const idRef = useRef(`mermaid-${Math.random().toString(36).substr(2, 9)}`);

  useEffect(() => {
    let cancelled = false;
    const renderChart = async () => {
      try {
        // Clean up any leftover broken render containers
        const oldEl = document.getElementById(idRef.current);
        if (oldEl) oldEl.remove();

        const { svg: renderedSvg } = await mermaid.render(idRef.current, chart.trim());
        if (!cancelled) {
          setSvg(renderedSvg);
          setError(false);
        }
      } catch (err: any) {
        // mermaid.render may leave broken elements in the DOM
        const brokenEl = document.getElementById(idRef.current);
        if (brokenEl) brokenEl.remove();
        if (!cancelled) {
          setSvg('');
          setError(true);
        }
      }
    };
    if (chart && chart.trim()) {
      renderChart();
    } else {
      setError(true);
    }
    return () => { cancelled = true; };
  }, [chart]);

  if (error || !svg) {
    return (
      <details style={{ margin: '12px 0' }}>
        <summary style={{ cursor: 'pointer', color: '#999', fontSize: 12 }}>
          图表源码（渲染失败，点击展开）
        </summary>
        <pre style={{ background: '#f6f8fa', padding: 12, borderRadius: 6, fontSize: 12, overflow: 'auto', border: '1px solid #e8e8e8', marginTop: 4 }}>
          <code>{chart}</code>
        </pre>
      </details>
    );
  }

  return (
    <div 
      dangerouslySetInnerHTML={{ __html: svg }} 
      style={{ textAlign: 'center', margin: '12px 0', overflow: 'auto' }}
    />
  );
};

/**
 * Splits markdown content into text segments and mermaid code blocks,
 * rendering each appropriately.
 */
const ReportContent: React.FC<{ content: string }> = ({ content }) => {
  const parts: { type: 'text' | 'mermaid'; content: string }[] = [];
  const regex = /```mermaid\s*\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', content: content.slice(lastIndex, match.index) });
    }
    parts.push({ type: 'mermaid', content: match[1] });
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < content.length) {
    parts.push({ type: 'text', content: content.slice(lastIndex) });
  }

  return (
    <div>
      {parts.map((part, idx) => 
        part.type === 'mermaid' ? (
          <MermaidChart key={idx} chart={part.content} />
        ) : (
          <MarkdownRenderer key={idx} content={part.content} />
        )
      )}
    </div>
  );
};

const ReportViewer: React.FC<ReportViewerProps> = ({ paperId }) => {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generateModalVisible, setGenerateModalVisible] = useState(false);
  const [focusDirections, setFocusDirections] = useState('');
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchReports = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/reports/', { params: { paper_id: paperId } });
      setReports(res.data);

      const hasGenerating = res.data.some((r: Report) => r.status === 'generating');
      setGenerating(hasGenerating);

      if (hasGenerating && !pollingRef.current) {
        pollingRef.current = setInterval(async () => {
          try {
            const pollRes = await api.get('/reports/', { params: { paper_id: paperId } });
            setReports(pollRes.data);
            const stillGenerating = pollRes.data.some((r: Report) => r.status === 'generating');
            if (!stillGenerating) {
              setGenerating(false);
              if (pollingRef.current) {
                clearInterval(pollingRef.current);
                pollingRef.current = null;
              }
              message.success('报告生成完成');
            }
          } catch {}
        }, 5000);
      }
    } catch (err) {
      message.error('获取报告失败');
    } finally {
      setLoading(false);
    }
  }, [paperId]);

  useEffect(() => {
    fetchReports();
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [paperId, fetchReports]);

  const handleOpenGenerate = () => {
    setFocusDirections('');
    setGenerateModalVisible(true);
  };

  const handleGenerate = async () => {
    setGenerateModalVisible(false);
    setGenerating(true);
    try {
      await api.post('/reports/generate', {
        paper_id: paperId,
        focus_directions: focusDirections.trim() || undefined,
      });
      message.info('报告生成任务已启动，Agent 将根据您的关注方向分析论文...');
      fetchReports();
    } catch (err: any) {
      message.error(err.response?.data?.detail || '启动报告生成失败');
      setGenerating(false);
    }
  };

  const handleDelete = async (reportId: string) => {
    try {
      await api.delete(`/reports/${reportId}`);
      message.success('报告已删除');
      fetchReports();
    } catch {
      message.error('删除失败');
    }
  };

  const handleDownload = (report: Report) => {
    const blob = new Blob([report.content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report.title || '阅读报告'}_v${report.version}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const formatTime = (seconds?: number) => {
    if (!seconds) return '';
    if (seconds < 60) return `${Math.round(seconds)}秒`;
    return `${Math.floor(seconds / 60)}分${Math.round(seconds % 60)}秒`;
  };

  if (loading && reports.length === 0) {
    return <div style={{ textAlign: 'center', padding: 40 }}><Spin size="large" /></div>;
  }

  return (
    <div style={{ height: 'calc(100vh - 180px)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 8px', borderBottom: '1px solid #f0f0f0', marginBottom: 8 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {reports.length > 0 ? `${reports.filter(r => r.status === 'completed').length} 份报告` : '暂无报告'}
        </Text>
        <Space>
          <Button size="small" icon={<ReloadOutlined />} onClick={fetchReports}>刷新</Button>
          <Button 
            size="small" 
            type="primary" 
            onClick={handleOpenGenerate} 
            loading={generating}
            disabled={generating}
          >
            {generating ? '生成中...' : '生成阅读报告'}
          </Button>
        </Space>
      </div>

      {/* Modal for focus directions input */}
      <Modal
        title="生成阅读报告"
        open={generateModalVisible}
        onOk={handleGenerate}
        onCancel={() => setGenerateModalVisible(false)}
        okText="开始生成"
        cancelText="取消"
        width={520}
      >
        <div style={{ marginBottom: 16 }}>
          <Paragraph type="secondary" style={{ marginBottom: 12 }}>
            Agent 将按照以下流程为您生成报告：
          </Paragraph>
          <div style={{ 
            background: '#f6f8fa', 
            borderRadius: 8, 
            padding: '12px 16px', 
            marginBottom: 16,
            fontSize: 13,
            lineHeight: '22px',
          }}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Text><Tag color="blue">Phase 1</Tag> 结合您的关注方向粗读论文，形成报告大纲</Text>
              <Text><Tag color="blue">Phase 2</Tag> 根据大纲精读论文原文，生成完整报告</Text>
            </Space>
          </div>
        </div>
        <div>
          <Text strong style={{ display: 'block', marginBottom: 8 }}>
            <AimOutlined style={{ marginRight: 4 }} />
            请输入您的重点关注方向（可选）：
          </Text>
          <TextArea
            value={focusDirections}
            onChange={(e) => setFocusDirections(e.target.value)}
            placeholder={
              '例如：\n' +
              '- 论文的核心算法创新点及其与传统方法的对比\n' +
              '- 模型在不同数据集上的泛化能力\n' +
              '- 该方法在工业界的实际应用前景\n\n' +
              '留空则全面分析论文各个方面'
            }
            autoSize={{ minRows: 4, maxRows: 8 }}
            style={{ fontSize: 13 }}
          />
          <Text type="secondary" style={{ fontSize: 12, marginTop: 4, display: 'block' }}>
            填写您最关心的方向，Agent 会在报告中重点展开这些内容
          </Text>
        </div>
      </Modal>

      <div style={{ flex: 1, overflowY: 'auto', padding: '0 4px' }}>
        {reports.length === 0 ? (
          <Empty 
            description="暂无阅读报告" 
            style={{ marginTop: 60 }}
          >
            <Button type="primary" onClick={handleOpenGenerate} disabled={generating}>
              生成第一份阅读报告
            </Button>
          </Empty>
        ) : (
          reports.map((report) => (
            <Card 
              key={report.id} 
              size="small" 
              style={{ marginBottom: 12, borderRadius: 8 }}
              title={
                <Space>
                  <Tag color="blue">v{report.version}</Tag>
                  {report.status === 'completed' && <Tag color="green">已完成</Tag>}
                  {report.status === 'generating' && <Tag color="processing" icon={<ClockCircleOutlined spin />}>生成中</Tag>}
                  {report.status === 'failed' && <Tag color="red">失败</Tag>}
                </Space>
              }
              extra={
                <Space>
                  {report.generation_time && (
                    <Text type="secondary" style={{ fontSize: 11 }}>耗时 {formatTime(report.generation_time)}</Text>
                  )}
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {new Date(report.created_at).toLocaleString()}
                  </Text>
                  {report.status === 'completed' && report.content && (
                    <Button type="text" size="small" icon={<DownloadOutlined />} onClick={() => handleDownload(report)} title="下载报告" />
                  )}
                  <Popconfirm title="确定删除此报告？" onConfirm={() => handleDelete(report.id)}>
                    <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                </Space>
              }
            >
              {/* Show focus directions if present */}
              {report.focus_directions && (
                <div style={{ 
                  background: '#f0f5ff', 
                  borderLeft: '3px solid #1890ff', 
                  padding: '8px 12px', 
                  marginBottom: 12, 
                  borderRadius: '0 4px 4px 0',
                  fontSize: 12,
                }}>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    <AimOutlined style={{ marginRight: 4 }} />
                    关注方向：
                  </Text>
                  <Text style={{ fontSize: 12 }}>{report.focus_directions}</Text>
                </div>
              )}
              {report.status === 'completed' && report.content && (
                <ReportContent content={report.content} />
              )}
              {report.status === 'generating' && (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Spin size="large" />
                  <div style={{ marginTop: 16 }}>
                    <Text type="secondary">
                      CrewAI Agent 正在分析论文并生成报告...
                    </Text>
                  </div>
                  <div style={{ marginTop: 8, fontSize: 12 }}>
                    <Text type="secondary">
                      Phase 1: 粗读论文 &rarr; 生成大纲 &rarr; Phase 2: 精读论文 &rarr; 撰写报告
                    </Text>
                  </div>
                </div>
              )}
              {report.status === 'failed' && (
                <Alert
                  type="error"
                  message="报告生成失败"
                  description={report.error_message || '未知错误'}
                  showIcon
                  action={
                    <Button size="small" type="primary" danger onClick={handleOpenGenerate}>
                      重试
                    </Button>
                  }
                />
              )}
            </Card>
          ))
        )}
      </div>
    </div>
  );
};

export default ReportViewer;
