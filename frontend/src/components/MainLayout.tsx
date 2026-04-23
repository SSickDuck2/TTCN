'use client';
import React, { useEffect, useState } from 'react';
import { ConfigProvider, Layout, App, Dropdown, Space, Button, Typography, Modal } from 'antd';
import { Inter } from 'next/font/google';
import { UserOutlined, LogoutOutlined, TeamOutlined, ShopOutlined, TrophyOutlined, FileTextOutlined, QuestionCircleOutlined, MessageOutlined, SettingOutlined } from '@ant-design/icons';
import { useRouter, usePathname } from 'next/navigation';
import { fetchApi } from '@/libs/api';
import TimeStatusBar from '@/components/TimeStatusBar';

const inter = Inter({ subsets: ['latin'] });
const { Header, Content, Footer } = Layout;
const { Text, Title, Paragraph } = Typography;

const HelpModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => (
  <Modal
    title={<><QuestionCircleOutlined style={{ color: '#1677ff', marginRight: 8 }} />Hướng dẫn sử dụng</>}
    open={visible}
    onCancel={onClose}
    footer={[
      <Button key="close" type="primary" onClick={onClose}>
        Đã hiểu
      </Button>,
    ]}
    width={700}
  >
    <div style={{ maxHeight: '60vh', overflowY: 'auto', paddingRight: 8 }}>
      <Typography>
        <Title level={4}>Chào mừng bạn đến với TTCN Market</Title>
        <Paragraph>Đây là nền tảng quản lý và chuyển nhượng cầu thủ bóng đá trực tuyến.</Paragraph>

        <Title level={5}>1. Thị trường cầu thủ</Title>
        <Paragraph>
          Tại trang <b>Thị trường</b>, bạn có thể tìm kiếm các cầu thủ từ nhiều giải đấu khác nhau. Bộ lọc bên trái giúp bạn lọc theo Vị trí, Giải đấu, Câu lạc bộ, Giá trị định giá, và Độ tuổi. Bộ lọc sẽ <b>tự động áp dụng</b> ngay khi bạn thay đổi thông số.
        </Paragraph>

        <Title level={5}>2. Xem chi tiết và Mua cầu thủ</Title>
        <Paragraph>
          Khi bấm vào <b>Chi tiết</b> một cầu thủ, bạn sẽ có 2 lựa chọn để sở hữu cầu thủ này:
          <ul>
            <li><b>Đấu giá trực tiếp:</b> Nếu cầu thủ đang ở trên thị trường tự do hoặc bị CLB rao bán công khai, bạn có thể đặt giá (Bid) tại đây. Trả giá cao hơn hiện tại để giành quyền sở hữu. Đấu giá có thời hạn nhất định.</li>
            <li><b>Hỏi mua (Đàm phán):</b> Nếu bạn muốn mua một cầu thủ đang thuộc biên chế một CLB khác, hãy bấm nút Hỏi mua (màu cam). Tính năng này sẽ khởi tạo một phiên đàm phán riêng tư với CLB chủ quản.</li>
          </ul>
        </Paragraph>

        <Title level={5}>3. Đàm phán trực tiếp</Title>
        <Paragraph>
          Tại trang <b>Đàm phán</b>, bạn sẽ trao đổi trực tiếp với máy (AI đóng vai trò CLB chủ quản). Quy trình đàm phán bao gồm:
          <ul>
            <li><b>Inquiry (Hỏi giá):</b> CLB chủ quản sẽ trả lời xem họ có muốn bán không và mức giá chào mời ban đầu.</li>
            <li><b>Hỏi đáp (Q&A):</b> Bạn có thể đặt câu hỏi để nắm bắt tình hình cầu thủ (chấn thương, thái độ, mức lương kỳ vọng, v.v.). AI sẽ phân tích và trả lời theo ngữ cảnh!</li>
            <li><b>Trả giá (Offer):</b> Bạn đưa ra mức giá của mình. CLB chủ quản có thể Đồng ý, Từ chối, hoặc Đưa ra mức giá phản hồi (Counter-Offer).</li>
          </ul>
        </Paragraph>

        <Title level={5}>4. Đội hình của bạn</Title>
        <Paragraph>
          Tại trang <b>Đội hình của tôi</b>, bạn có thể quản lý các cầu thủ mình đang sở hữu, xem chi tiết đội hình và tổng quỹ lương của CLB.
        </Paragraph>
      </Typography>
    </div>
  </Modal>
);

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [clubInfo, setClubInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [helpVisible, setHelpVisible] = useState(false);

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
      key: 'trade',
      label: 'Đàm phán',
      icon: <MessageOutlined />,
      onClick: () => router.push('/trade/negotiate'),
    },
    {
      key: 'admin',
      label: 'Admin',
      icon: <SettingOutlined />,
      onClick: () => router.push('/trade/admin'),
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
              <a
                onClick={() => router.push('/trade/negotiate')}
                style={{
                  color: pathname.includes('/negotiate') ? '#1677ff' : '#595959',
                  fontWeight: pathname.includes('/negotiate') ? 600 : 400,
                  textDecoration: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6
                }}
              >
                <FileTextOutlined /> Đàm phán
              </a>

              <a
                onClick={() => router.push('/trade/admin')}
                style={{
                  color: pathname.includes('/admin') ? '#1677ff' : '#595959',
                  fontWeight: pathname.includes('/admin') ? 600 : 400,
                  textDecoration: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6
                }}
              >
                <SettingOutlined /> Admin
              </a>

              <div style={{ width: '1px', height: '24px', background: '#f0f0f0', margin: '0 8px' }} />

              <Button
                type="text"
                icon={<QuestionCircleOutlined />}
                onClick={() => setHelpVisible(true)}
                style={{ color: '#595959' }}
              >
                Hướng dẫn
              </Button>

              <TimeStatusBar />

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
        <HelpModal visible={helpVisible} onClose={() => setHelpVisible(false)} />
      </App>
    </ConfigProvider>
  );
}
