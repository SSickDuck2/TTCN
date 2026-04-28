'use client';
import { useState, useEffect } from 'react';
import { Table, Tag, Typography, Card, Button, App, InputNumber, Row, Col, Statistic } from 'antd';
import { fetchApi } from '@/libs/api';
import { useRouter } from 'next/navigation';
import { WalletOutlined, TeamOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

const POSITION_COLORS: Record<string, string> = {
  GK: 'gold', DF: 'blue', MF: 'green', FW: 'red',
};

export default function SquadPage() {
  const [players, setPlayers] = useState([]);
  const [clubInfo, setClubInfo] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { message, modal } = App.useApp();

  const loadData = async () => {
    setLoading(true);
    try {
      const [squadData, meData] = await Promise.all([
        fetchApi('/squad'),
        fetchApi('/me')
      ]);
      setPlayers(squadData);
      setClubInfo(meData);
    } catch (error) {
      message.error('Lỗi khi tải dữ liệu');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const formatMoney = (value: number) => {
    return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR', minimumFractionDigits: 0 }).format(value);
  };

  const handleQuickSell = (playerId: number, name: string, marketValue: number) => {
    modal.confirm({
      title: `Chắc chắn bán nhanh ${name}?`,
      content: `Giá trị nhận lại bằng 80% định giá: ${formatMoney(marketValue * 0.8)}`,
      onOk: async () => {
        try {
          await fetchApi('/squad/sell', {
            method: 'POST',
            body: JSON.stringify({ player_id: playerId, sell_type: 'quick_sell' })
          });
          message.success(`Đã bán ${name}`);
          loadData();
        } catch (error: any) {
          message.error(error.message || 'Lỗi khi bán');
        }
      }
    });
  };

  const columns = [
    { title: 'Tên cầu thủ', dataIndex: 'name', key: 'name', render: (text: string, record: any) => (
      <a onClick={() => router.push(`/trade/player/${record.player_id}`)} style={{ fontWeight: 'bold' }}>{text}</a>
    ) },
    { title: 'Vị trí', dataIndex: 'position', key: 'position', render: (pos: string) => (
      <Tag color={POSITION_COLORS[pos] || 'default'} style={{ minWidth: 40, textAlign: 'center' }}>{pos}</Tag>
    ) },
    { title: 'Giải đấu', dataIndex: 'league', key: 'league' },
    { title: 'Định giá', dataIndex: 'market_value', key: 'market_value', render: (val: number) => <Text strong>{formatMoney(val)}</Text> },
    {
      title: 'Hành động',
      key: 'action',
      align: 'right' as const,
      render: (_: any, record: any) => (
        <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
          <Button type="primary" danger size="small" onClick={() => handleQuickSell(record.player_id, record.name, record.market_value)}>Bán nhanh</Button>
        </div>
      ),
    },
  ];

  return (
    <div style={{ paddingBottom: 40 }}>
      <Row gutter={[24, 24]} align="middle" style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Title level={2} style={{ margin: 0 }}>Đội hình của tôi</Title>
        </Col>
        <Col span={12} style={{ textAlign: 'right' }}>
          <Card size="small" style={{ display: 'inline-block', borderRadius: 8, boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
            <Statistic
              title="Ngân sách khả dụng"
              value={clubInfo?.budget_remaining || 0}
              precision={0}
              prefix={<WalletOutlined style={{ color: '#52c41a' }} />}
              suffix="€"
              valueStyle={{ color: '#3f8600', fontSize: '1.2rem', fontWeight: 700 }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[24, 24]}>
        <Col span={24}>
          <Card bordered={false} style={{ borderRadius: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
            <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <TeamOutlined style={{ fontSize: 20, color: '#1677ff' }} />
              <Text strong style={{ fontSize: 16 }}>Danh sách cầu thủ ({players.length})</Text>
            </div>
            <Table 
              columns={columns} 
              dataSource={players} 
              rowKey="player_id" 
              loading={loading} 
              pagination={false}
              size="middle"
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
