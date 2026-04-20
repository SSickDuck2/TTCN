'use client';
import { useState, useEffect } from 'react';
import { Card, Typography, Descriptions, Spin, message, Row, Col, InputNumber, Button, Badge, Timeline } from 'antd';
import { fetchApi } from '@/libs/api';
import { useParams } from 'next/navigation';

export default function PlayerDetail() {
  const params = useParams();
  const playerId = params.id;
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [bidding, setBidding] = useState(false);
  const [socketBids, setSocketBids] = useState<any[]>([]);
  const [currentPrice, setCurrentPrice] = useState(0);
  const [highestBidder, setHighestBidder] = useState('Không có');

  useEffect(() => {
    if (!playerId) return;
    
    // Load initial data
    const loadPlayer = async () => {
      try {
        const res = await fetchApi(`/player/${playerId}`);
        setData(res.player);
        if (res.auction) {
          setCurrentPrice(res.auction.current_price);
          setHighestBidder(res.auction.highest_bidder);
        }
      } catch (err) {
        message.error('Không tìm thấy cầu thủ');
      } finally {
        setLoading(false);
      }
    };
    loadPlayer();

    // Setup Socket
    const ws = new WebSocket(`ws://localhost:8000/ws/auction/${playerId}`);
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'new_bid') {
        setCurrentPrice(msg.current_price);
        setHighestBidder(msg.highest_bidder);
        setSocketBids(prev => [{
          time: new Date().toLocaleTimeString(),
          amount: msg.current_price,
          bidder: msg.highest_bidder
        }, ...prev]);
        message.info(`Có giá thầu mới: ${formatMoney(msg.current_price)} từ ${msg.highest_bidder}`);
      } else if (msg.type === 'auction_closed') {
        message.success(`Đấu giá kết thúc! ${msg.player_name} đã thuộc về CLB với giá ${formatMoney(msg.final_price)}`);
      }
    };

    return () => {
      ws.close();
    };
  }, [playerId]);

  const formatMoney = (value: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'EUR', minimumFractionDigits: 0 }).format(value);
  };

  const handleBid = async (amount: number) => {
    setBidding(true);
    try {
      await fetchApi('/market/bid', {
        method: 'POST',
        body: JSON.stringify({ listing_id: Number(playerId), bid_amount: amount })
      });
      message.success('Gửi giá thành công!');
    } catch (err: any) {
      message.error(err.message || 'Lỗi đặt giá');
    } finally {
      setBidding(false);
    }
  };

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }}><Spin size="large" /></div>;
  if (!data) return <Typography.Title level={3}>Cầu thủ không tồn tại</Typography.Title>;

  return (
    <div>
      <Row gutter={[24, 24]}>
        <Col span={16}>
          <Card title={<Typography.Title level={3} style={{ margin: 0 }}>Thông tin: {data.name}</Typography.Title>}>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="CLB Hiện tại">{data.club}</Descriptions.Item>
              <Descriptions.Item label="Vị trí">{data.position}</Descriptions.Item>
              <Descriptions.Item label="Quốc gia">{data.nation}</Descriptions.Item>
              <Descriptions.Item label="Độ tuổi">{data.age}</Descriptions.Item>
              <Descriptions.Item label="Giải đấu">{data.league}</Descriptions.Item>
              <Descriptions.Item label="Định giá">{formatMoney(data.market_value)}</Descriptions.Item>
              
              <Descriptions.Item label="Số trận">{data.stats?.matches}</Descriptions.Item>
              <Descriptions.Item label="Đá chính">{data.stats?.starts}</Descriptions.Item>
              <Descriptions.Item label="Số phút thi đấu">{data.stats?.minutes}</Descriptions.Item>
              <Descriptions.Item label="Bàn thắng">{data.stats?.goals}</Descriptions.Item>
              <Descriptions.Item label="Kiến tạo">{data.stats?.assists}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col span={8}>
          <Card title="Live Đấu giá" bordered={false} style={{ background: '#fafafa' }}>
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <Typography.Text type="secondary">Giá hiện tại</Typography.Text>
              <Typography.Title level={2} style={{ color: '#eb2f96', margin: '10px 0' }}>
                {formatMoney(currentPrice || data.market_value)}
              </Typography.Title>
              <Typography.Text strong>Đang dẫn đầu: <Badge status="processing" text={highestBidder} /></Typography.Text>
            </div>

            <div style={{ marginTop: 24 }}>
              <InputNumber
                id="bidAmount"
                style={{ width: '100%', marginBottom: 10 }}
                step={500000}
                defaultValue={(currentPrice || data.market_value) + 100000}
                formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              />
              <Button type="primary" block size="large" loading={bidding} onClick={() => {
                const val = (document.getElementById('bidAmount') as any)?.value.replace(/,/g, '');
                handleBid(Number(val));
              }}>
                Ra giá ngay
              </Button>
            </div>

            {socketBids.length > 0 && (
              <div style={{ marginTop: 24 }}>
                <Typography.Title level={5}>Lịch sử ra giá (Live)</Typography.Title>
                <Timeline>
                  {socketBids.map((b, i) => (
                    <Timeline.Item key={i} color={i === 0 ? 'green' : 'gray'}>
                      {b.time} - {b.bidder} cược <b>{formatMoney(b.amount)}</b>
                    </Timeline.Item>
                  ))}
                </Timeline>
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
