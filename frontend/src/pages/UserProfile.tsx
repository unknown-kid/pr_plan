import React, { useEffect, useState } from 'react';
import { Layout, Card, Avatar, Typography, List, Button, Space, Switch, message, Divider } from 'antd';
import { UserOutlined, StarOutlined, HistoryOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import useUserStore from '../store/userStore';
import { personalizationService, paperService } from '../services/paperService';

const { Header, Content } = Layout;
const { Title, Text } = Typography;

const UserProfile: React.FC = () => {
  const navigate = useNavigate();
  const { user, darkMode, setDarkMode } = useUserStore();
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const res = await personalizationService.getFavorites();
        // For each favorite, fetch paper details (simplified for now)
        setFavorites(res.data);
      } catch (err) {
        message.error('获取收藏失败');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', borderBottom: '1px solid #f0f0f0', display: 'flex', alignItems: 'center' }}>
        <ArrowLeftOutlined onClick={() => navigate('/')} style={{ cursor: 'pointer', marginRight: 16 }} />
        <Title level={4} style={{ margin: 0 }}>个人中心</Title>
      </Header>
      <Content style={{ padding: '24px', maxWidth: '800px', margin: '0 auto', width: '100%' }}>
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
            <Avatar size={80} icon={<UserOutlined />} />
            <div>
              <Title level={3} style={{ margin: 0 }}>{user?.username || '用户'}</Title>
              <Text type="secondary">{user?.email || 'email@example.com'}</Text>
            </div>
          </div>
          <Divider />
          <Space direction="vertical" style={{ width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text>深色模式</Text>
              <Switch checked={darkMode} onChange={setDarkMode} />
            </div>
          </Space>
        </Card>

        <Card title={<span><StarOutlined /> 我的收藏</span>} style={{ marginTop: '24px' }}>
          <List
            loading={loading}
            dataSource={favorites}
            renderItem={(item: any) => (
              <List.Item
                actions={[<Button type="link" onClick={() => navigate(`/papers/${item.paper_id}`)}>查看</Button>]}
              >
                <List.Item.Meta
                  title={`论文 ID: ${item.paper_id}`}
                  description={`收藏时间: ${new Date(item.created_at).toLocaleString()}`}
                />
              </List.Item>
            )}
          />
        </Card>
      </Content>
    </Layout>
  );
};

export default UserProfile;
