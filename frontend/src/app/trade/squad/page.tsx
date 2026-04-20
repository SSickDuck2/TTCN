'use client';
import { useState, useEffect } from 'react';
import { Table, Tag, Typography, Card, Button, Modal, message, InputNumber } from 'antd';
import { fetchApi } from '@/libs/api';
import { useRouter } from 'next/navigation';

export default function SquadPage() {
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const loadSquad = async () => {
    setLoading(true);
    try {
      const data = await fetchApi('/squad');
      setPlayers(data);
    } catch (error) {
      message.error('Lỗi khi tải đội hình');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSquad();
  }, []);

  const formatMoney = (value: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'EUR', minimumFractionDigits: 0 }).format(value);
  };

  const handleQuickSell = (playerId: number, name: string, marketValue: number) => {
    Modal.confirm({
      title: `Chắc chắn bán nhanh ${name}?`,
      content: `Giá trị nhận lại bằng 80% định giá: ${formatMoney(marketValue * 0.8)}`,
      onOk: async () => {
        try {
          await fetchApi('/squad/sell', {
            method: 'POST',
            body: JSON.stringify({ player_id: playerId, sell_type: 'quick_sell' })
          });
          message.success(`Đã bán ${name}`);
          loadSquad();
        } catch (error: any) {
          message.error(error.message || 'Lỗi khi bán');
        }
      }
    });
  };

  const handleAuction = (playerId: number, name: string) => {
    Modal.confirm({
      title: `Đưa ${name} lên sàn đấu giá?`,
      content: <div>
        <p>Chọn thời gian đấu giá (phút):</p>
        <InputNumber min={5} max={120} defaultValue={30} id={`duration_${playerId}`} style={{ width: '100%' }} />
      </div>,
      onOk: async () => {
        const duration = (document.getElementById(`duration_${playerId}`) as any)?.value || 30;
        try {
          await fetchApi('/squad/sell', {
            method: 'POST',
            body: JSON.stringify({ player_id: playerId, sell_type: 'auction', duration_minutes: Number(duration) })
          });
          message.success(`Đã đưa ${name} lên sàn đấu giá`);
          loadSquad();
        } catch (error: any) {
          message.error(error.message || 'Lỗi khi đưa lên đấu giá');
        }
      }
    });
  };

  const columns = [
    { title: 'Tên cầu thủ', dataIndex: 'name', key: 'name', render: (text: string, record: any) => (
      <a onClick={() => router.push(`/trade/player/${record.player_id}`)} style={{ fontWeight: 'bold' }}>{text}</a>
    ) },
    { title: 'Vị trí', dataIndex: 'position', key: 'position', render: (pos: string) => <Tag color="blue">{pos}</Tag> },
    { title: 'Giải đấu', dataIndex: 'league', key: 'league' },
    { title: 'Định giá', dataIndex: 'market_value', key: 'market_value', render: (val: number) => formatMoney(val) },
    {
      title: 'Hành động',
      key: 'action',
      render: (_: any, record: any) => (
        <div style={{ display: 'flex', gap: '8px' }}>
          <Button type="primary" danger size="small" onClick={() => handleQuickSell(record.player_id, record.name, record.market_value)}>Bán liền</Button>
          <Button type="default" size="small" onClick={() => handleAuction(record.player_id, record.name)}>Lên đấu giá</Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <Typography.Title level={2}>Đội hình của tôi</Typography.Title>
      <Card style={{ borderRadius: 8 }}>
        <Table columns={columns} dataSource={players} rowKey="player_id" loading={loading} />
      </Card>
    </div>
  );
}
