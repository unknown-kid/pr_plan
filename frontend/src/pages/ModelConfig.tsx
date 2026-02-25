import React, { useEffect, useState } from 'react';
import { Layout, Table, Button, Space, Modal, Form, Input, Select, Switch, message, Card, Typography, Popconfirm } from 'antd';
import { PlusOutlined, DeleteOutlined, ArrowLeftOutlined, StarOutlined, StarFilled, EditOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

const { Header, Content } = Layout;
const { Title } = Typography;
const { Option } = Select;

const ModelConfig: React.FC = () => {
  const [models, setModels] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [visible, setVisible] = useState(false);
  const [testing, setTesting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  const fetchModels = async () => {
    setLoading(true);
    try {
      const res = await api.get('/models/');
      setModels(res.data);
    } catch (err) {
      message.error('获取模型列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const handleOpenModal = (record?: any) => {
    if (record) {
      setEditingId(record.id);
      form.setFieldsValue(record);
    } else {
      setEditingId(null);
      form.resetFields();
    }
    setVisible(true);
  };

  const handleSubmit = async (values: any) => {
    try {
      if (editingId) {
        await api.put(`/models/${editingId}`, values);
        message.success('更新成功');
      } else {
        await api.post('/models/', values);
        message.success('添加成功');
      }
      setVisible(false);
      form.resetFields();
      fetchModels();
    } catch (err) {
      message.error(editingId ? '更新失败' : '添加失败');
    }
  };

  const handleTest = async () => {
    const values = await form.validateFields();
    setTesting(true);
    try {
      const res = await api.post('/models/test-connectivity', values);
      if (res.data.status === 'success') {
        message.success(res.data.message);
      } else {
        message.error(res.data.message);
      }
    } catch (err: any) {
      message.error(err.response?.data?.detail || '测试失败，请检查网络和配置');
    } finally {
      setTesting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/models/${id}`);
      message.success('删除成功');
      fetchModels();
    } catch (err) {
      message.error('删除失败');
    }
  };

  const handleSetDefault = async (id: string) => {
    try {
      await api.put(`/models/${id}/set-default`);
      message.success('已设为默认');
      fetchModels();
    } catch (err) {
      message.error('设置失败');
    }
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    { 
      title: '类型', 
      dataIndex: 'model_type', 
      key: 'model_type',
      render: (val: string) => {
        const labels: Record<string, string> = {
          chat: '对话模型',
          embedding: '嵌入模型',
          translation: '翻译模型'
        };
        return labels[val] || val;
      }
    },
    { title: '供应商', dataIndex: 'provider', key: 'provider' },
    { title: '模型名', dataIndex: 'model_name', key: 'model_name' },
    { 
      title: '默认', 
      dataIndex: 'is_default', 
      key: 'is_default',
      render: (val: boolean, record: any) => (
        <Button 
          type='link' 
          icon={val ? <StarFilled style={{ color: '#fadb14' }} /> : <StarOutlined />} 
          onClick={() => !val && handleSetDefault(record.id)}
          disabled={val}
        >
          {val ? '默认' : '设为默认'}
        </Button>
      )
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space>
          <Button icon={<EditOutlined />} onClick={() => handleOpenModal(record)} size="small" />
          <Popconfirm title="确定删除吗？" onConfirm={() => handleDelete(record.id)}>
            <Button icon={<DeleteOutlined />} danger size="small" />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', borderBottom: '1px solid #f0f0f0', display: 'flex', alignItems: 'center', padding: '0 16px' }}>
        <ArrowLeftOutlined onClick={() => navigate('/')} style={{ cursor: 'pointer', marginRight: 16 }} />
        <Title level={4} style={{ margin: 0 }}>AI模型配置</Title>
      </Header>
      <Content style={{ padding: '24px' }}>
        <Card 
          title="我的模型配置" 
          extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => handleOpenModal()}>添加配置</Button>}
          bodyStyle={{ padding: 0 }}
        >
          <Table dataSource={models} columns={columns} rowKey="id" loading={loading} pagination={false} />
        </Card>
        <Card size="small" style={{ marginTop: 16, background: '#fffbe6', border: '1px solid #ffe58f' }}>
          <Typography.Text type="secondary">
            提示：您可以为对话、嵌入和翻译分别设置一个默认模型。对于翻译模型，请选择DeepL供应商并填写DeepL API Key。
          </Typography.Text>
        </Card>
      </Content>

      <Modal
        title={editingId ? "编辑 AI 模型" : "添加 AI 模型"}
        open={visible}
        onCancel={() => setVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setVisible(false)}>取消</Button>,
          <Button key="test" icon={<CheckCircleOutlined />} onClick={handleTest} loading={testing}>测试连通性</Button>,
          <Button key="submit" type="primary" onClick={() => form.submit()}>保存</Button>,
        ]}
      >
        <Form form={form} onFinish={handleSubmit} layout="vertical">
          <Form.Item name="name" label="配置名称" rules={[{ required: true }]}>
            <Input placeholder="例如：我的 DeepL 翻译服务" />
          </Form.Item>
          <Form.Item name="model_type" label="模型类型" initialValue="chat">
            <Select>
              <Option value="chat">对话模型</Option>
              <Option value="embedding">嵌入模型</Option>
              <Option value="translation">翻译模型</Option>
            </Select>
          </Form.Item>
          <Form.Item name="provider" label="供应商" initialValue="openai">
            <Select>
              <Option value="openai">OpenAI (or compatible)</Option>
              <Option value="anthropic">Anthropic</Option>
              <Option value="local">Local (Ollama/LM Studio)</Option>
              <Option value="deepl">DeepL</Option>
            </Select>
          </Form.Item>
          <Form.Item name="api_url" label="API URL">
            <Input placeholder="https://api.openai.com/v1 (DeepL: https://api-free.deepl.com/v2/translate)" />
          </Form.Item>
          <Form.Item name="api_key" label="API Key">
            <Input.Password placeholder={editingId ? "留空则保持不变" : "API Key (DeepL: Auth Key)"} />
          </Form.Item>
          <Form.Item name="model_name" label="模型名称" rules={[{ required: form.getFieldValue('provider') !== 'deepl' }]}>
            <Input placeholder="gpt-4-turbo-preview (DeepL不需要)" />
          </Form.Item>
          <Form.Item name="is_default" label="设为默认" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  );
};

export default ModelConfig;
