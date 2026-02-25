import React, { useState } from 'react';
import { Card, Form, Input, Button, Tabs, message, Typography } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import useUserStore from '../store/userStore';

const { Title } = Typography;

const Login: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('login');
  const navigate = useNavigate();
  const { setToken, setUser } = useUserStore();

  const onFinish = async (values: any) => {
    setLoading(true);
    try {
      if (activeTab === 'login') {
        const formData = new URLSearchParams();
        formData.append('username', values.username);
        formData.append('password', values.password);
        
        const res = await api.post('/auth/login', formData, {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });
        setToken(res.data.access_token);
        
        // Get user info
        const userRes = await api.get('/auth/me');
        setUser(userRes.data);
        
        message.success('登录成功');
        navigate('/');
      } else {
        await api.post('/auth/register', {
          username: values.username,
          email: values.email,
          password: values.password
        });
        message.success('注册成功，请登录');
        setActiveTab('login');
      }
    } catch (err: any) {
      message.error(err.response?.data?.detail || '操作失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      minHeight: '100vh',
      background: '#f0f2f5' 
    }}>
      <Card style={{ width: 400, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={2}>Paper Reader</Title>
        </div>
        <Tabs activeKey={activeTab} onChange={setActiveTab} centered items={[
          {
            key: 'login',
            label: '登录',
            children: (
              <Form onFinish={onFinish} layout="vertical">
                <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                  <Input prefix={<UserOutlined />} placeholder="用户名或邮箱" />
                </Form.Item>
                <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
                  <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit" loading={loading} block>登录</Button>
                </Form.Item>
              </Form>
            )
          },
          {
            key: 'register',
            label: '注册',
            children: (
              <Form onFinish={onFinish} layout="vertical">
                <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                  <Input prefix={<UserOutlined />} placeholder="用户名" />
                </Form.Item>
                <Form.Item name="email" rules={[{ required: true, type: 'email', message: '请输入有效邮箱' }]}>
                  <Input prefix={<MailOutlined />} placeholder="电子邮箱" />
                </Form.Item>
                <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }, { min: 6, message: '密码至少6位' }]}>
                  <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit" loading={loading} block>注册</Button>
                </Form.Item>
              </Form>
            )
          }
        ]} />
      </Card>
    </div>
  );
};

export default Login;
