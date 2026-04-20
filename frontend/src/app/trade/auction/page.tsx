'use client';
import { useState, useEffect } from 'react';
import { Table, Typography, Card, message } from 'antd';
import { fetchApi } from '@/libs/api';
import { useRouter } from 'next/navigation';

export default function AuctionManagementPage() {
  const [auctions, setAuctions] = useState([]);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const loadData = async () => {
    setLoading(true);
    try {
      const { players } = await fetchApi('/market/players?page=1'); 
      // Instead of getting all players, we will rely on /market/auctions for active
      const activeAuctions = await fetchApi('/market/auctions');
      setAuctions(activeAuctions);
    } catch (error) {
      message.error('Lỗi khi tải đấu giá');
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

  const columns = [
    { title: 'Tên cầu thủ', dataIndex: 'player_name', key: 'player_name', render: (text: string, record: any) => (
      <a onClick={() => router.push(`/trade/player/${record.player_id}`)} style={{ fontWeight: 'bold' }}>{text}</a>
    ) },
    { title: 'Đang đấu', dataIndex: 'current_price', key: 'current_price', render: (val: number) => <span style={{ color: '#52c41a', fontWeight: 'bold' }}>{formatMoney(val)}</span> },
    { title: 'Kết thúc', dataIndex: 'auction_end_time', key: 'end_time', render: (val: string) => new Date(val).toLocaleString() },
  ];

  return (
    <div>
      <Typography.Title level={2}>Danh sách đang đấu</Typography.Title>
      <Card style={{ borderRadius: 8 }}>
        <Table columns={columns} dataSource={auctions} rowKey="listing_id" loading={loading} />
      </Card>
    </div>
  );
}
