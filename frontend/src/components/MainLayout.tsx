'use client';
import React, { useEffect, useState } from 'react';
import { ConfigProvider, Layout, App, Dropdown, Menu, Space, Button, Typography } from 'antd';
import { Inter } from 'next/font/google';
import { UserOutlined, LogoutOutlined, TeamOutlined, ShopOutlined, TrophyOutlined } from '@ant-design/icons';
import { useRouter, usePathname } from 'next/navigation';
import { fetchApi } from '@/libs/api';

const inter = Inter({ subsets: ['latin'] });
const { Header, Content, Footer } = Layout;
const { Text } = Typography;

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [clubInfo, setClubInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadClub = async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      setClubInfo(null);
      setLoading(false);
      return;
    }
    try {
      const res = await fetchApi('/me');
      setClubInfo(res);
    } catch {
      localStorage.removeItem('token');
      setClubInfo(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClub();
  }, [pathname]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    setClubInfo(null);
    router.push('/');
  };

  const userMenuItems = [
    {
      key: 'squad',
      label: 'Đội hình của tôi',
      icon: <TeamOutlined />,
      onClick: () => router.push('/trade/squad'),
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      label: 'Đăng xuất',
      icon: <LogoutOutlined />,
      danger: true,
      onClick: handleLogout,
    },
  ];

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#1677ff',
          fontFamily: inter.style.fontFamily,
        },
      }}
    >
      <App>
        <Layout style={{ minHeight: '100vh', background: '#f5f5f5' }}>
          <Header
            style={{
              display: 'flex',
              alignItems: 'center',
              background: '#ffffff',
              padding: '0 24px',
              position: 'sticky',
              top: 0,
              zIndex: 10,
              width: '100%',
              boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
            }}
          >
            <div style={{ color: '#1677ff', fontSize: '1.2rem', fontWeight: 'bold', display: 'flex', alignItems: 'center' }}>
              <a onClick={() => router.push('/trade/market')} style={{ color: '#1677ff', textDecoration: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 32, height: 32, background: '#1677ff', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 'bold' }}>
                  T
                </div>
                TTCN
              </a>
            </div>

            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '32px' }}>
              <a
                onClick={() => router.push('/trade/market')}
                style={{
                  color: pathname.includes('/market') ? '#1677ff' : '#595959',
                  fontWeight: pathname.includes('/market') ? 600 : 400,
                  textDecoration: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6
                }}
              >
                <ShopOutlined /> Thị trường
              </a>
              <a
                onClick={() => router.push('/trade/auction')}
                style={{
                  color: pathname.includes('/auction') ? '#1677ff' : '#595959',
                  fontWeight: pathname.includes('/auction') ? 600 : 400,
                  textDecoration: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6
                }}
              >
                <TrophyOutlined /> Quản lý Đấu giá
              </a>

              <div style={{ width: '1px', height: '24px', background: '#f0f0f0', margin: '0 8px' }} />

              {loading ? (
                <div style={{ width: 100, height: 20, background: '#f0f0f0', borderRadius: 4 }} />
              ) : clubInfo ? (
                <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" arrow>
                  <Button type="text" style={{ display: 'flex', alignItems: 'center', gap: 8, height: 40 }}>
                    <div style={{ width: 24, height: 24, background: '#e6f4ff', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#1677ff' }}>
                      <UserOutlined style={{ fontSize: 12 }} />
                    </div>
                    <Text strong>{clubInfo.name}</Text>
                  </Button>
                </Dropdown>
              ) : (
                <Button type="primary" onClick={() => router.push('/')}>Đăng nhập</Button>
              )}
            </div>
          </Header>
          <Content style={{ padding: '24px 48px', maxWidth: '1400px', margin: '0 auto', width: '100%' }}>
            {children}
          </Content>
          <Footer style={{ textAlign: 'center', background: 'transparent', color: '#8c8c8c', padding: '40px 0' }}>
            TTCN Transfermarkt Data ©{new Date().getFullYear()}
          </Footer>
        </Layout>
      </App>
    </ConfigProvider>
  );
}
