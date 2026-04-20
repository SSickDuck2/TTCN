'use client';
import { useState, useEffect } from 'react';
import { Table, Tag, Input, Typography, Card, Button, InputNumber, Row, Col, message } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { fetchApi } from '@/libs/api';
import { useRouter } from 'next/navigation';

export default function Market() {
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [auctions, setAuctions] = useState([]);
  const router = useRouter();

  const loadData = async () => {
    setLoading(true);
    try {
      const [playersRes, auctionsRes] = await Promise.all([
        fetchApi('/market/players?page=1'),
        fetchApi('/market/auctions'),
      ]);
      setPlayers(playersRes.players);
      setAuctions(auctionsRes);
    } catch (error: any) {
      message.error('Lỗi khi tải dữ liệu thị trường');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const formatMoney = (value: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'EUR', minimumFractionDigits: 0 }).format(value);
  };

  const onBid = async (listingId: number, amount: number) => {
    try {
      await fetchApi('/market/bid', {
        method: 'POST',
        body: JSON.stringify({ listing_id: listingId, bid_amount: amount }),
      });
      message.success('Đặt giá thành công!');
      loadData();
    } catch (error: any) {
      message.error(error.message || 'Lỗi đặt giá');
    }
  };

  const columns = [
    {
      title: 'Tên cầu thủ',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: any) => (
        <a onClick={() => router.push(`/trade/player/${record.player_id}`)} style={{ fontWeight: 'bold' }}>{text}</a>
      ),
    },
    {
      title: 'Vị trí',
      dataIndex: 'position',
      key: 'position',
      render: (pos: string) => <Tag color="blue">{pos}</Tag>,
    },
    {
      title: 'CLB hiện tại',
      dataIndex: 'club',
      key: 'club',
    },
    {
      title: 'Giải đấu',
      dataIndex: 'league',
      key: 'league',
    },
    {
      title: 'Định giá',
      dataIndex: 'market_value',
      key: 'market_value',
      render: (val: number) => formatMoney(val),
    },
  ];

  const auctionColumns = [
    { title: 'Tên cầu thủ', dataIndex: 'player_name', key: 'player_name', render: (text: string, record: any) => (
      <a onClick={() => router.push(`/trade/player/${record.player_id}`)} style={{ fontWeight: 'bold' }}>{text}</a>
    ) },
    { title: 'Giá hiện tại', dataIndex: 'current_price', key: 'current_price', render: (val: number) => <span style={{ color: '#52c41a', fontWeight: 'bold' }}>{formatMoney(val)}</span> },
    { title: 'Kết thúc', dataIndex: 'auction_end_time', key: 'end_time', render: (val: string) => new Date(val).toLocaleString() },
  ];

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={2} style={{ margin: 0 }}>Thị trường chuyển nhượng</Typography.Title>
        <Input placeholder="Tìm kiếm cầu thủ..." prefix={<SearchOutlined />} style={{ width: 300 }} />
      </div>

      <Row gutter={[24, 24]}>
        <Col span={16}>
          <Card title="Danh sách cầu thủ" style={{ borderRadius: 8 }}>
            <Table
              columns={columns}
              dataSource={players}
              rowKey="player_id"
              loading={loading}
              pagination={{ pageSize: 15 }}
            />
          </Card>
        </Col>
        
        <Col span={8}>
          <Card title="Đấu giá đang diễn ra 🔥" style={{ borderRadius: 8 }}>
            <Table
              columns={auctionColumns}
              dataSource={auctions}
              rowKey="listing_id"
              loading={loading}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
