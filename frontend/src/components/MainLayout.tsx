'use client';
import React from 'react';
import { ConfigProvider, Layout } from 'antd';
import { Inter } from 'next/font/google';
import LogoutLink from '@/components/LogoutLink';

const inter = Inter({ subsets: ['latin'] });
const { Header, Content, Footer } = Layout;

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#1677ff',
          fontFamily: inter.style.fontFamily,
        },
      }}
    >
      <Layout style={{ minHeight: '100vh', background: '#f5f5f5' }}>
        <Header
          style={{
            display: 'flex',
            alignItems: 'center',
            background: '#001529',
            padding: '0 24px',
            position: 'sticky',
            top: 0,
            zIndex: 1,
            width: '100%',
          }}
        >
          <div style={{ color: 'white', fontSize: '1.2rem', fontWeight: 'bold' }}>
            <a href="/trade/market" style={{ color: 'white', textDecoration: 'none' }}>
              ⚽ TTCN Market
            </a>
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: '15px' }}>
            <a href="/trade/market" style={{ color: 'white', textDecoration: 'none' }}>Thị trường</a>
            <a href="/trade/squad" style={{ color: 'white', textDecoration: 'none' }}>Đội hình</a>
            <a href="/trade/auction" style={{ color: 'white', textDecoration: 'none' }}>Quản lý đấu giá</a>
            <LogoutLink />
          </div>
        </Header>
        <Content style={{ padding: '24px 48px', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
          {children}
        </Content>
        <Footer style={{ textAlign: 'center', background: '#f5f5f5', color: '#888' }}>
          TTCN Transfermarkt Data ©{new Date().getFullYear()}
        </Footer>
      </Layout>
    </ConfigProvider>
  );
}
