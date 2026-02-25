import React, { useEffect, useState, useRef } from 'react';
import { 
  Layout, Menu, Button, Input, Space, Tag, Modal, Form, Upload, message, 
  Card, Select, Dropdown, Popconfirm, Empty, Spin, Progress, 
  Tabs, List, Typography, Checkbox, Radio, Tree, Pagination, Tooltip
} from 'antd';
import { 
  UploadOutlined, SearchOutlined, UserOutlined, SettingOutlined, 
  BookOutlined, DeleteOutlined, FolderOutlined, FolderAddOutlined, 
  FileTextOutlined, HomeOutlined, LinkOutlined, ReloadOutlined, 
  CloseOutlined, FolderOpenOutlined, ThunderboltOutlined, RightOutlined,
  DragOutlined, DownloadOutlined, MoreOutlined, EllipsisOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { paperService } from '../services/paperService';
import useUserStore from '../store/userStore';
import api from '../services/api';

const { Header, Content, Sider } = Layout;
const { Text } = Typography;

interface Folder {
  id: string;
  name: string;
  parent_id: string | null;
  paper_count: number;
  created_at: string;
}

interface Paper {
  id: string;
  title: string;
  status: string;
  folder_id: string | null;
  created_at: string;
}

interface DuplicateFileAction {
  name: string;
  file: File;
  action: 'replace' | 'skip' | 'rename';
  existingPaperId?: string;
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

const Home: React.FC = () => {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploadVisible, setUploadVisible] = useState(false);
  const [createFolderVisible, setCreateFolderVisible] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [currentFolder, setCurrentFolder] = useState<Folder | null>(null);
  const [folderPath, setFolderPath] = useState<Folder[]>([]);
  const [uploadProgress, setUploadProgress] = useState({ current: 0, total: 0, visible: false });
  const [uploadMode, setUploadMode] = useState<'file' | 'url'>('file');
  const [urlList, setUrlList] = useState('');
  const [urlTitle, setUrlTitle] = useState('');
  const [urlEmbeddingModelId, setUrlEmbeddingModelId] = useState<string | undefined>();
  const [models, setModels] = useState<any[]>([]);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [moveModalVisible, setMoveModalVisible] = useState(false);
  const [allFolders, setAllFolders] = useState<Folder[]>([]);
  const [moveTargetFolderId, setMoveTargetFolderId] = useState<string | null>(null);
  const [duplicateFiles, setDuplicateFiles] = useState<DuplicateFileAction[]>([]);
  const [duplicateModalVisible, setDuplicateModalVisible] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [totalCount, setTotalCount] = useState(0);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [searchResults, setSearchResults] = useState<{papers: Paper[], folders: Folder[], total: number} | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [hoveredRow, setHoveredRow] = useState<string | null>(null);
  
  const navigate = useNavigate();
  const { logout } = useUserStore();
  const formRef = useRef<any>(null);

  // ── Data fetching ───────────────────────────────
  const fetchData = async () => {
    setLoading(true);
    try {
      const [papersRes, foldersRes] = await Promise.all([
        paperService.list({ 
          skip: (currentPage - 1) * pageSize, 
          limit: pageSize,
          folder_id: currentFolder?.id || 'null'
        }),
        api.get('/folders/', { params: currentFolder ? { parent_id: currentFolder.id } : {} })
      ]);
      
      setPapers(papersRes.data.papers || papersRes.data);
      setTotalCount(papersRes.data.total || papersRes.data.length);
      setFolders(foldersRes.data);
    } catch (err) {
      message.error('获取数据失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchModels = async () => {
    try {
      const res = await api.get('/models/');
      setModels(res.data.filter((m: any) => m.model_type === 'embedding'));
    } catch (err) {}
  };

  useEffect(() => { fetchData(); }, [currentFolder, currentPage, pageSize]);
  useEffect(() => { fetchModels(); }, []);
  useEffect(() => { setCurrentPage(1); }, [currentFolder]);
  useEffect(() => { setSearchKeyword(''); setSearchResults(null); }, [currentFolder]);

  useEffect(() => {
    const timer = setTimeout(() => { if (searchKeyword) handleSearch(searchKeyword); }, 300);
    return () => clearTimeout(timer);
  }, [searchKeyword]);

  const handleSearch = async (keyword: string) => {
    if (!keyword || keyword.trim() === '') { setSearchResults(null); return; }
    setIsSearching(true);
    try {
      const res = await api.get('/papers/search', {
        params: { keyword: keyword.trim(), folder_id: currentFolder?.id || 'null', limit: 100 }
      });
      setSearchResults(res.data);
    } catch (err) { message.error('搜索失败'); }
    finally { setIsSearching(false); }
  };

  const filteredFolders = searchResults ? searchResults.folders : folders.filter(f => 
    f.name.toLowerCase().includes(searchKeyword.toLowerCase())
  );
  const filteredPapers = searchResults ? searchResults.papers : papers.filter(p => 
    p.title.toLowerCase().includes(searchKeyword.toLowerCase())
  );

  // ── Upload ──────────────────────────────────────
  const checkDuplicates = async (files: File[]) => {
    const currentPaperNames = papers.map(p => ({ title: p.title.toLowerCase(), id: p.id }));
    const duplicates: {name: string, file: File, existingPaperId?: string}[] = [];
    const unique: File[] = [];
    for (const file of files) {
      const name = file.name.replace(/\.pdf$/i, '').toLowerCase();
      const existing = currentPaperNames.find(p => p.title === name);
      if (existing) {
        duplicates.push({ name: file.name.replace(/\.pdf$/i, ''), file, existingPaperId: existing.id });
      } else {
        unique.push(file);
      }
    }
    return { duplicates, unique };
  };

  const handleBatchUpload = async (values: any) => {
    const files = values.files?.fileList || [];
    if (files.length === 0) { message.error('请选择文件'); return; }
    const fileObjects = files.map((f: any) => f.originFileObj);
    const { duplicates, unique } = await checkDuplicates(fileObjects);
    if (duplicates.length > 0) {
      setDuplicateFiles(duplicates.map(d => ({ name: d.name, file: d.file, action: 'skip' as const, existingPaperId: d.existingPaperId })));
      setPendingFiles(unique);
      setDuplicateModalVisible(true);
      return;
    }
    await processUpload(unique, values.embedding_model_id);
  };

  const processUpload = async (files: File[], embeddingModelId?: string, fileActions?: Map<string, {action: string, existingId?: string}>) => {
    const total = files.length;
    setUploadProgress({ current: 0, total, visible: true });
    setUploadVisible(false);
    setDuplicateModalVisible(false);
    let successCount = 0, failCount = 0;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const formData = new FormData();
      let title = file.name.replace(/\.pdf$/i, '');
      const fileAction = fileActions?.get(file.name);
      if (fileAction?.action === 'rename') title = `${title}_${Date.now()}`;
      else if (fileAction?.action === 'replace' && fileAction.existingId) {
        try { await api.delete(`/papers/${fileAction.existingId}/permanent`); } catch {}
      }
      formData.append('title', title);
      formData.append('file', file);
      if (currentFolder) formData.append('folder_id', currentFolder.id);
      if (embeddingModelId) formData.append('embedding_model_id', embeddingModelId);

      try { await api.post('/papers/', formData, { headers: { 'Content-Type': 'multipart/form-data' } }); successCount++; }
      catch { failCount++; }
      setUploadProgress(prev => ({ ...prev, current: i + 1 }));
    }
    setUploadProgress({ current: 0, total: 0, visible: false });
    if (formRef.current) formRef.current.resetFields();
    if (successCount > 0) { message.success(`成功上传 ${successCount} 篇论文`); fetchData(); }
    if (failCount > 0) message.error(`${failCount} 篇论文上传失败`);
  };

  const handleConfirmDuplicates = async () => {
    const actions = new Map<string, {action: string, existingId?: string}>();
    duplicateFiles.forEach(d => actions.set(d.file.name, { action: d.action, existingId: d.existingPaperId }));
    const filesToUpload = duplicateFiles.filter(d => d.action !== 'skip').map(d => d.file);
    await processUpload([...filesToUpload, ...pendingFiles], undefined, actions);
  };

  const handleDuplicateFileAction = (index: number, action: 'replace' | 'skip' | 'rename') => {
    const newDuplicates = [...duplicateFiles];
    newDuplicates[index] = { ...newDuplicates[index], action };
    setDuplicateFiles(newDuplicates);
  };

  const handleUrlUpload = async () => {
    const urls = urlList.split('\n').map(u => u.trim()).filter(u => u);
    if (urls.length === 0) { message.error('请输入PDF链接'); return; }
    setUploadProgress({ current: 0, total: urls.length, visible: true });
    setUploadVisible(false);
    let successCount = 0, failCount = 0;
    for (const url of urls) {
      try {
        await api.post('/papers/url', { url, title: urlTitle || url.split('/').pop() || 'Untitled', folder_id: currentFolder?.id, embedding_model_id: urlEmbeddingModelId });
        successCount++;
      } catch { failCount++; }
      setUploadProgress(prev => ({ ...prev, current: prev.current + 1 }));
    }
    setUploadProgress({ current: 0, total: 0, visible: false });
    setUrlList(''); setUrlTitle('');
    if (successCount > 0) { message.success(`成功上传 ${successCount} 篇论文`); fetchData(); }
    if (failCount > 0) message.error(`${failCount} 篇论文上传失败`);
  };

  // ── Folder operations ──────────────────────────
  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) { message.error('请输入文件夹名称'); return; }
    try {
      await api.post('/folders/', { name: newFolderName, parent_id: currentFolder?.id || null });
      message.success('文件夹创建成功');
      setCreateFolderVisible(false); setNewFolderName(''); fetchData();
    } catch { message.error('创建文件夹失败'); }
  };

  const handleDeleteFolder = async (folderId: string) => {
    try { await api.delete(`/folders/${folderId}/permanent`); message.success('文件夹已删除'); fetchData(); }
    catch { message.error('删除失败'); }
  };

  // ── Paper operations ───────────────────────────
  const handleDeletePaper = async (paperId: string) => {
    try { await api.delete(`/papers/${paperId}/permanent`); message.success('论文已删除'); fetchData(); }
    catch { message.error('删除失败'); }
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

  // ── Batch operations ───────────────────────────
  const handleBatchDelete = () => {
    const selectedList = Array.from(selectedItems);
    const folderCount = folders.filter(f => selectedList.includes(f.id)).length;
    const paperCount = papers.filter(p => selectedList.includes(p.id)).length;
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除选中的 ${folderCount > 0 ? folderCount + ' 个文件夹' : ''}${folderCount > 0 && paperCount > 0 ? '和 ' : ''}${paperCount > 0 ? paperCount + ' 篇论文' : ''}吗？此操作不可撤销。`,
      okType: 'danger',
      onOk: async () => {
        try {
          for (const id of selectedList) {
            if (folders.find(f => f.id === id)) await api.delete(`/folders/${id}/permanent`);
            else await api.delete(`/papers/${id}/permanent`);
          }
          message.success('已删除');
          setSelectedItems(new Set()); fetchData();
        } catch { message.error('删除失败'); }
      }
    });
  };

  const handleSelectItem = (id: string, checked: boolean) => {
    const newSelected = new Set(selectedItems);
    if (checked) newSelected.add(id); else newSelected.delete(id);
    setSelectedItems(newSelected);
  };

  const handleSelectAll = () => {
    const allIds = [...filteredFolders.map(f => f.id), ...filteredPapers.map(p => p.id)];
    if (selectedItems.size === allIds.length && allIds.length > 0) setSelectedItems(new Set());
    else setSelectedItems(new Set(allIds));
  };

  const handleBatchVectorize = async () => {
    const paperIds = Array.from(selectedItems).filter(id => papers.some(p => p.id === id));
    if (paperIds.length === 0) { message.warning('请选择论文'); return; }
    try {
      await api.post('/batch/', { operation_type: 'vectorize', paper_ids: paperIds });
      message.success('批量向量化任务已启动'); setSelectedItems(new Set());
    } catch { message.error('批量操作失败'); }
  };

  const handleOpenMoveModal = async () => {
    if (selectedItems.size === 0) { message.warning('请先选择要移动的项目'); return; }
    try { const res = await api.get('/folders/all'); setAllFolders(res.data); }
    catch { setAllFolders([]); }
    setMoveTargetFolderId(null); setMoveModalVisible(true);
  };

  const handleBatchMove = async () => {
    const selectedList = Array.from(selectedItems);
    const itemIds: string[] = [], itemTypes: string[] = [];
    for (const id of selectedList) {
      itemIds.push(id);
      itemTypes.push(folders.some(f => f.id === id) ? 'folder' : 'paper');
    }
    try {
      await api.post('/folders/batch/move', { item_ids: itemIds, item_types: itemTypes, target_folder_id: moveTargetFolderId });
      message.success(`已移动 ${itemIds.length} 个项目`);
      setSelectedItems(new Set()); setMoveModalVisible(false); fetchData();
    } catch { message.error('移动失败'); }
  };

  const buildFolderTreeData = (folderList: Folder[]): any[] => {
    const selectedList = Array.from(selectedItems);
    const excludeIds = new Set(selectedList.filter(id => folders.some(f => f.id === id)));
    const getChildren = (parentId: string | null): any[] => {
      return folderList
        .filter(f => f.parent_id === parentId && !excludeIds.has(f.id))
        .map(f => ({ title: f.name, key: f.id, icon: <FolderOutlined />, children: getChildren(f.id) }));
    };
    return [{ title: '根目录（我的论文）', key: '__root__', icon: <HomeOutlined />, children: getChildren(null) }];
  };

  // ── Navigation ─────────────────────────────────
  const handleNavigateToFolder = (folder: Folder) => {
    setCurrentFolder(folder); setFolderPath([...folderPath, folder]); setSelectedItems(new Set());
  };

  const handleNavigateToPath = (index: number) => {
    setSelectedItems(new Set());
    if (index === -1) { setCurrentFolder(null); setFolderPath([]); }
    else { setCurrentFolder(folderPath[index]); setFolderPath(folderPath.slice(0, index + 1)); }
  };

  const handlePageChange = (page: number, newPageSize?: number) => {
    setCurrentPage(page);
    if (newPageSize && newPageSize !== pageSize) { setPageSize(newPageSize); setCurrentPage(1); }
  };

  const handleItemNameClick = (id: string, type: 'folder' | 'paper', e: React.MouseEvent) => {
    e.stopPropagation();
    if (selectedItems.size > 0) { handleSelectItem(id, !selectedItems.has(id)); return; }
    if (type === 'folder') { const folder = folders.find(f => f.id === id); if (folder) handleNavigateToFolder(folder); }
    else window.open(`/papers/${id}`, '_blank');
  };

  const handleRowClick = (id: string, e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.closest('button') || target.closest('.ant-popconfirm') || 
        target.closest('.file-name-link') || target.closest('.ant-checkbox-wrapper') ||
        target.closest('.ant-dropdown-trigger') || target.closest('.ant-dropdown')) return;
    handleSelectItem(id, !selectedItems.has(id));
  };

  // ── Dropdown menus ─────────────────────────────
  const getPaperDropdownItems = (paper: Paper) => ({
    items: [
      { key: 'open', label: '打开论文', onClick: () => window.open(`/papers/${paper.id}`, '_blank') },
      { key: 'download', label: '下载 PDF', icon: <DownloadOutlined />, onClick: () => handleDownloadPaper(paper.id, paper.title) },
      { key: 'vectorize', label: '向量化', icon: <ThunderboltOutlined />, onClick: async () => {
        try { await api.post('/batch/', { operation_type: 'vectorize', paper_ids: [paper.id] }); message.success('向量化任务已启动'); }
        catch { message.error('操作失败'); }
      }},
      { type: 'divider' as const },
      { key: 'delete', label: '删除', icon: <DeleteOutlined />, danger: true, onClick: () => {
        Modal.confirm({ title: '确认删除', content: `确定要删除论文「${paper.title}」吗？此操作不可撤销。`, okType: 'danger',
          onOk: () => handleDeletePaper(paper.id)
        });
      }},
    ]
  });

  const getFolderDropdownItems = (folder: Folder) => ({
    items: [
      { key: 'open', label: '打开文件夹', onClick: () => handleNavigateToFolder(folder) },
      { type: 'divider' as const },
      { key: 'delete', label: '删除', icon: <DeleteOutlined />, danger: true, onClick: () => {
        Modal.confirm({ title: '确认删除', content: `确定要删除文件夹「${folder.name}」及其所有内容吗？此操作不可撤销。`, okType: 'danger',
          onOk: () => handleDeleteFolder(folder.id)
        });
      }},
    ]
  });

  // ── Shared row styles ──────────────────────────
  const allIds = [...filteredFolders.map(f => f.id), ...filteredPapers.map(p => p.id)];
  const isAllSelected = selectedItems.size === allIds.length && allIds.length > 0;
  const isIndeterminate = selectedItems.size > 0 && selectedItems.size < allIds.length;

  const getRowStyle = (id: string): React.CSSProperties => ({
    padding: '10px 16px',
    background: selectedItems.has(id) ? '#e6f7ff' : hoveredRow === id ? '#fafafa' : 'transparent',
    borderRadius: 6,
    marginBottom: 2,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    transition: 'background 0.15s',
    borderBottom: '1px solid #f0f0f0',
  });

  // ── Render ─────────────────────────────────────
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible width={220}>
        <div style={{ height: 32, margin: 16, background: 'rgba(255, 255, 255, 0.2)', color: 'white', textAlign: 'center', lineHeight: '32px', fontWeight: 'bold' }}>
          Paper Reader
        </div>
        <Menu theme="dark" selectedKeys={['1']} mode="inline">
          <Menu.Item key="1" icon={<BookOutlined />} onClick={() => { setCurrentFolder(null); setFolderPath([]); }}>我的论文</Menu.Item>
          <Menu.Item key="2" icon={<SearchOutlined />} onClick={() => navigate('/search')}>全文搜索</Menu.Item>
          <Menu.Item key="3" icon={<SettingOutlined />} onClick={() => navigate('/config')}>模型配置</Menu.Item>
          <Menu.Item key="4" icon={<UserOutlined />} onClick={() => navigate('/profile')}>个人中心</Menu.Item>
        </Menu>
      </Sider>
      
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #f0f0f0' }}>
          <Space>
            <Button icon={<FolderAddOutlined />} onClick={() => setCreateFolderVisible(true)}>新建文件夹</Button>
            <Button icon={<UploadOutlined />} type="primary" onClick={() => setUploadVisible(true)}>上传论文</Button>
          </Space>
          <Button onClick={logout}>退出登录</Button>
        </Header>
        
        <Content style={{ margin: '16px 24px' }}>
          <Card 
            title={
              <Space>
                <span style={{ fontSize: 16, fontWeight: 600 }}>论文库</span>
                {folderPath.length > 0 && (
                  <>
                    <span style={{ color: '#d9d9d9', margin: '0 4px' }}>/</span>
                    <a onClick={() => handleNavigateToPath(-1)} style={{ color: '#1890ff', fontSize: 14 }}>
                      <HomeOutlined /> 根目录
                    </a>
                    {folderPath.map((folder, index) => (
                      <React.Fragment key={folder.id}>
                        <span style={{ color: '#d9d9d9', margin: '0 4px' }}>/</span>
                        {index === folderPath.length - 1 ? (
                          <span style={{ color: '#333', fontSize: 14 }}>{folder.name}</span>
                        ) : (
                          <a onClick={() => handleNavigateToPath(index)} style={{ color: '#1890ff', fontSize: 14 }}>{folder.name}</a>
                        )}
                      </React.Fragment>
                    ))}
                  </>
                )}
              </Space>
            }
            extra={
              <Space>
                {selectedItems.size > 0 && (
                  <>
                    <Text type="secondary">已选 {selectedItems.size} 项</Text>
                    <Button size="small" icon={<CloseOutlined />} onClick={() => setSelectedItems(new Set())}>取消</Button>
                  </>
                )}
                <Button onClick={fetchData} icon={<ReloadOutlined />} size="small">刷新</Button>
              </Space>
            }
            bodyStyle={{ padding: '16px 0' }}
          >
            {/* Toolbar */}
            <div style={{ padding: '0 24px 12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #f0f0f0' }}>
              <Space>
                <Checkbox checked={isAllSelected} indeterminate={isIndeterminate} onChange={handleSelectAll}>全选</Checkbox>
                {selectedItems.size > 0 && (
                  <>
                    <Button size="small" icon={<DragOutlined />} onClick={handleOpenMoveModal}>移动到</Button>
                    <Button size="small" icon={<ThunderboltOutlined />} onClick={handleBatchVectorize}>向量化</Button>
                    <Button size="small" danger icon={<DeleteOutlined />} onClick={handleBatchDelete}>删除</Button>
                  </>
                )}
              </Space>
              <Space>
                <Input
                  placeholder="搜索论文或文件夹..."
                  prefix={<SearchOutlined style={{ color: '#bfbfbf' }} />}
                  value={searchKeyword}
                  onChange={(e) => { setSearchKeyword(e.target.value); if (!e.target.value) setSearchResults(null); }}
                  style={{ width: 260 }}
                  allowClear
                  size="small"
                  suffix={isSearching ? <Spin size="small" /> : null}
                />
                {searchResults && (
                  <Tag color="blue">找到 {searchResults.total} 个结果</Tag>
                )}
              </Space>
            </div>

            {/* Column header */}
            <div style={{ padding: '8px 24px', display: 'flex', alignItems: 'center', color: '#8c8c8c', fontSize: 12, fontWeight: 500, borderBottom: '1px solid #f0f0f0' }}>
              <span style={{ width: 36 }} />
              <span style={{ width: 28 }} />
              <span style={{ flex: 1 }}>名称</span>
              <span style={{ width: 80, textAlign: 'center' }}>状态</span>
              <span style={{ width: 100, textAlign: 'center' }}>添加时间</span>
              <span style={{ width: 48, textAlign: 'center' }}>操作</span>
            </div>
            
            {uploadProgress.visible && (
              <div style={{ padding: '12px 24px' }}>
                <Progress 
                  percent={Math.round((uploadProgress.current / uploadProgress.total) * 100)} 
                  status="active"
                  format={() => `${uploadProgress.current} / ${uploadProgress.total}`}
                />
              </div>
            )}

            <div style={{ padding: '0 8px' }}>
              {loading || isSearching ? (
                <div style={{ textAlign: 'center', padding: '60px 0' }}><Spin size="large" /></div>
              ) : filteredFolders.length === 0 && filteredPapers.length === 0 ? (
                <Empty description={searchKeyword ? "未找到匹配的文件" : "当前文件夹为空"} style={{ padding: '60px 0' }} />
              ) : (
                <>
                  {/* Folder rows */}
                  {filteredFolders.map(folder => (
                    <div
                      key={folder.id}
                      onClick={(e) => handleRowClick(folder.id, e)}
                      onMouseEnter={() => setHoveredRow(folder.id)}
                      onMouseLeave={() => setHoveredRow(null)}
                      style={getRowStyle(folder.id)}
                    >
                      <Checkbox
                        checked={selectedItems.has(folder.id)}
                        style={{ marginRight: 12 }}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) => handleSelectItem(folder.id, e.target.checked)}
                      />
                      <FolderOutlined style={{ fontSize: 18, color: '#faad14', marginRight: 10 }} />
                      <span 
                        className="file-name-link"
                        style={{ flex: 1, fontWeight: 500, color: '#1890ff', cursor: 'pointer', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                        onClick={(e) => handleItemNameClick(folder.id, 'folder', e)}
                      >
                        {folder.name}
                      </span>
                      <span style={{ width: 80, textAlign: 'center' }}>
                        <Tag style={{ margin: 0 }}>{folder.paper_count || 0} 篇</Tag>
                      </span>
                      <span style={{ width: 100, textAlign: 'center', color: '#8c8c8c', fontSize: 13 }}>
                        {formatDate(folder.created_at)}
                      </span>
                      <span style={{ width: 48, textAlign: 'center' }}>
                        <Dropdown menu={getFolderDropdownItems(folder)} trigger={['click']}>
                          <Button type="text" size="small" icon={<EllipsisOutlined />} onClick={(e) => e.stopPropagation()} />
                        </Dropdown>
                      </span>
                    </div>
                  ))}
                  
                  {/* Paper rows */}
                  {filteredPapers.map(paper => (
                    <div
                      key={paper.id}
                      onClick={(e) => handleRowClick(paper.id, e)}
                      onMouseEnter={() => setHoveredRow(paper.id)}
                      onMouseLeave={() => setHoveredRow(null)}
                      style={getRowStyle(paper.id)}
                    >
                      <Checkbox
                        checked={selectedItems.has(paper.id)}
                        style={{ marginRight: 12 }}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) => handleSelectItem(paper.id, e.target.checked)}
                      />
                      <FileTextOutlined style={{ fontSize: 18, color: '#1890ff', marginRight: 10 }} />
                      <Tooltip title={paper.title} mouseEnterDelay={0.5}>
                        <span 
                          className="file-name-link"
                          style={{ flex: 1, fontWeight: 500, color: '#1890ff', cursor: 'pointer', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                          onClick={(e) => handleItemNameClick(paper.id, 'paper', e)}
                        >
                          {paper.title}
                        </span>
                      </Tooltip>
                      <span style={{ width: 80, textAlign: 'center' }}>
                        {getStatusDisplay(paper.status)}
                      </span>
                      <span style={{ width: 100, textAlign: 'center', color: '#8c8c8c', fontSize: 13 }}>
                        {formatDate(paper.created_at)}
                      </span>
                      <span style={{ width: 48, textAlign: 'center' }}>
                        <Dropdown menu={getPaperDropdownItems(paper)} trigger={['click']}>
                          <Button type="text" size="small" icon={<EllipsisOutlined />} onClick={(e) => e.stopPropagation()} />
                        </Dropdown>
                      </span>
                    </div>
                  ))}
                  
                  {totalCount > pageSize && (
                    <div style={{ marginTop: 16, padding: '0 16px', textAlign: 'right' }}>
                      <Pagination
                        current={currentPage} pageSize={pageSize} total={totalCount}
                        onChange={handlePageChange} showSizeChanger
                        showTotal={(total) => `共 ${total} 篇`}
                        pageSizeOptions={['10', '20', '50', '100']}
                        size="small"
                      />
                    </div>
                  )}
                </>
              )}
            </div>
          </Card>
        </Content>
      </Layout>

      {/* Upload Modal */}
      <Modal
        title="上传论文" open={uploadVisible}
        onCancel={() => { setUploadVisible(false); setUrlList(''); setUrlTitle(''); if (formRef.current) formRef.current.resetFields(); }}
        footer={null} width={600}
      >
        <Tabs activeKey={uploadMode} onChange={(key) => setUploadMode(key as 'file' | 'url')} items={[
          { key: 'file', label: '文件上传', children: (
            <Form ref={formRef} onFinish={handleBatchUpload} layout="vertical">
              <Form.Item name="files" label="PDF 文件（支持多选）" rules={[{ required: true }]}>
                <Upload multiple beforeUpload={() => false} accept=".pdf">
                  <Button icon={<UploadOutlined />}>选择文件</Button>
                  <span style={{ marginLeft: 8, color: '#999' }}>可同时选择多个文件</span>
                </Upload>
              </Form.Item>
              <Form.Item name="embedding_model_id" label="嵌入模型">
                <Select placeholder="使用默认模型" allowClear>
                  {models.map(m => <Select.Option key={m.id} value={m.id}>{m.name} ({m.model_name})</Select.Option>)}
                </Select>
              </Form.Item>
              {currentFolder && <div style={{ marginBottom: 16, color: '#666' }}>将上传到文件夹：<Tag color="blue">{currentFolder.name}</Tag></div>}
              <Form.Item><Button type="primary" htmlType="submit">开始上传</Button></Form.Item>
            </Form>
          )},
          { key: 'url', label: 'URL上传', children: (
            <div>
              <Input.TextArea placeholder="输入PDF下载链接，每行一个" value={urlList} onChange={(e) => setUrlList(e.target.value)} rows={4} style={{ marginBottom: 16 }} />
              <Input placeholder="默认标题（可选）" value={urlTitle} onChange={(e) => setUrlTitle(e.target.value)} style={{ marginBottom: 16 }} />
              <Select placeholder="选择嵌入模型" allowClear style={{ width: '100%', marginBottom: 16 }} value={urlEmbeddingModelId} onChange={setUrlEmbeddingModelId}>
                {models.map(m => <Select.Option key={m.id} value={m.id}>{m.name} ({m.model_name})</Select.Option>)}
              </Select>
              {currentFolder && <div style={{ marginBottom: 16, color: '#666' }}>将上传到文件夹：<Tag color="blue">{currentFolder.name}</Tag></div>}
              <Button type="primary" onClick={handleUrlUpload} block>开始上传</Button>
            </div>
          )}
        ]} />
      </Modal>

      {/* Move Modal */}
      <Modal title="移动到文件夹" open={moveModalVisible} onCancel={() => setMoveModalVisible(false)} onOk={handleBatchMove} okText="移动" cancelText="取消" width={480}>
        <div style={{ marginBottom: 12 }}><Text type="secondary">选择目标文件夹，将 {selectedItems.size} 个项目移动到指定位置：</Text></div>
        <div style={{ maxHeight: 400, overflow: 'auto', border: '1px solid #d9d9d9', borderRadius: 6, padding: 8 }}>
          <Tree showIcon defaultExpandAll treeData={buildFolderTreeData(allFolders)}
            selectedKeys={moveTargetFolderId ? [moveTargetFolderId] : ['__root__']}
            onSelect={(keys) => { if (keys.length > 0) { const key = keys[0] as string; setMoveTargetFolderId(key === '__root__' ? null : key); }}}
          />
        </div>
      </Modal>

      {/* Create Folder Modal */}
      <Modal title="新建文件夹" open={createFolderVisible} onCancel={() => setCreateFolderVisible(false)} onOk={handleCreateFolder}>
        <Input placeholder="输入文件夹名称" value={newFolderName} onChange={(e) => setNewFolderName(e.target.value)} onPressEnter={handleCreateFolder} />
        {currentFolder && <div style={{ marginTop: 8, color: '#666' }}>将创建在文件夹 <Tag color="blue">{currentFolder.name}</Tag> 下</div>}
      </Modal>

      {/* Duplicate Files Modal */}
      <Modal title="发现重复文件" open={duplicateModalVisible}
        onCancel={() => { setDuplicateModalVisible(false); setDuplicateFiles([]); setPendingFiles([]); }}
        onOk={handleConfirmDuplicates} okText="确认上传" cancelText="取消" width={650}
      >
        <div style={{ marginBottom: 16 }}><Text type="warning">当前文件夹中已存在同名文件，请选择处理方式：</Text></div>
        <List size="small" dataSource={duplicateFiles}
          renderItem={(item, index) => (
            <List.Item>
              <div style={{ display: 'flex', alignItems: 'center', width: '100%', justifyContent: 'space-between' }}>
                <Text strong style={{ flex: 1 }}>{item.name}.pdf</Text>
                <Radio.Group value={item.action} onChange={(e) => handleDuplicateFileAction(index, e.target.value)} size="small" optionType="button" buttonStyle="solid">
                  <Radio.Button value="replace">替换</Radio.Button>
                  <Radio.Button value="skip">跳过</Radio.Button>
                  <Radio.Button value="rename">保留两者</Radio.Button>
                </Radio.Group>
              </div>
            </List.Item>
          )}
          style={{ maxHeight: 300, overflow: 'auto' }}
        />
        <div style={{ marginTop: 16, padding: 12, background: '#fffbe6', borderRadius: 4, border: '1px solid #ffe58f' }}>
          <Text type="secondary">
            <strong>选项说明：</strong><br/>
            • 替换：删除原文件，上传新文件<br/>
            • 跳过：不上传该文件<br/>
            • 保留两者：自动重命名新文件
          </Text>
        </div>
        {pendingFiles.length > 0 && <div style={{ marginTop: 12 }}><Text type="secondary">另外 {pendingFiles.length} 个文件无重复，将直接上传</Text></div>}
      </Modal>
    </Layout>
  );
};

export default Home;
