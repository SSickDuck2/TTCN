'use client';
import { useState, useEffect, useMemo } from 'react';
import {
  Card, Typography, Descriptions, Spin, App, Row, Col, Tag,
  InputNumber, Button, Badge, Timeline, Table, Space, Divider,
} from 'antd';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip as RechartsTooltip,
} from 'recharts';
import { fetchApi } from '@/libs/api';
import { useParams, useRouter } from 'next/navigation';
import { ArrowUpOutlined, HistoryOutlined, TrophyOutlined, MessageOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

const formatLeague = (l: string) => {
  const mapping: Record<string, string> = {
    'epl': 'Premier League',
    'la_liga': 'La Liga',
    'ligue_1': 'Ligue 1',
    'bundesliga': 'Bundesliga',
    'serie_a': 'Serie A'
  };
  return mapping[l] || l;
};

export default function PlayerDetail() {
  const params = useParams();
  const playerId = params.id;
  const { message } = App.useApp();

  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [bidding, setBidding] = useState(false);
  const [inquiring, setInquiring] = useState(false);
  const [hasNego, setHasNego] = useState(false);
  const [socketBids, setSocketBids] = useState<any[]>([]);
  const [currentPrice, setCurrentPrice] = useState(0);
  const [highestBidder, setHighestBidder] = useState('Chưa có');
  const [bidValue, setBidValue] = useState<number>(0);
  const [myClub, setMyClub] = useState<string | null>(null);
  const [positionAvg, setPositionAvg] = useState<any>(null);

  useEffect(() => {
    if (!playerId) return;

    const loadPlayer = async () => {
      try {
        const [res, me, negos] = await Promise.all([
          fetchApi(`/player/${playerId}`),
          fetchApi('/me').catch(() => null),
          fetchApi('/negotiations/my').catch(() => [])
        ]);
        
        setData(res.player);
        setMyClub(me?.name || null);
        setPositionAvg(res.position_avg);

        // Check if current player is in my negotiations
        const existing = negos.find((n: any) => n.player_id === Number(playerId));
        if (existing) setHasNego(true);

        if (res.auction) {
          setCurrentPrice(res.auction.current_price);
          setHighestBidder(res.auction.highest_bidder);
          const basePrice = Math.max(res.auction.current_price, res.player.market_value);
          setBidValue(basePrice + 500000);
          if (res.auction.bid_history) {
            setSocketBids(res.auction.bid_history.map((b: any) => ({
              ...b,
              time: new Date(b.time).toLocaleTimeString('vi-VN')
            })));
          }
        } else if (res.player) {
          setBidValue(res.player.market_value + 500000);
        }
      } catch (err) {
        message.error('Không tìm thấy cầu thủ');
      } finally {
        setLoading(false);
      }
    };
    loadPlayer();

    const ws = new WebSocket(`ws://localhost:8000/ws/auction/${playerId}`);
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'new_bid') {
        setCurrentPrice(msg.current_price);
        setHighestBidder(msg.highest_bidder);
        setBidValue(msg.current_price + 500000);
        setSocketBids(prev => [{
          time: new Date().toLocaleTimeString('vi-VN'),
          amount: msg.current_price,
          bidder: msg.highest_bidder
        }, ...prev]);
        message.info(`Giá thầu mới: ${formatMoney(msg.current_price)} từ ${msg.highest_bidder}`);
      } else if (msg.type === 'auction_closed') {
        message.success(`Đấu giá kết thúc! ${msg.player_name} đã được bán với giá ${formatMoney(msg.final_price)}`);
      }
    };

    return () => ws.close();
  }, [playerId, message]);

  const formatMoney = (value: number) => {
    return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR', minimumFractionDigits: 0 }).format(value);
  };

  const handleBid = async (amount: number) => {
    const basePrice = Math.max(currentPrice, data?.market_value || 0);
    if (amount <= basePrice) {
      message.warning('Giá thầu phải cao hơn giá hiện tại');
      return;
    }
    setBidding(true);
    try {
      await fetchApi('/market/bid', {
        method: 'POST',
        body: JSON.stringify({ listing_id: Number(playerId), bid_amount: amount })
      });
      message.success('Đặt giá thành công!');
    } catch (err: any) {
      message.error(err.message || 'Lỗi đặt giá');
    } finally {
      setBidding(false);
    }
  };

  const handleInquire = async () => {
    setInquiring(true);
    try {
      await fetchApi('/negotiations/inquire', {
        method: 'POST',
        body: JSON.stringify({ player_id: Number(playerId) })
      });
      message.success('Đã gửi yêu cầu hỏi mua thành công. Vui lòng kiểm tra tab Đàm phán!');
      router.push(`/trade/negotiate`);
    } catch (err: any) {
      message.error(err.message || 'Lỗi khởi tạo đàm phán');
    } finally {
      setInquiring(false);
    }
  };

  const radarData = useMemo(() => {
    if (!data || !data.stats || !positionAvg) return [];
    const stats = data.stats;
    const mins = stats.minutes || 1;
    const per90 = (val: number) => (val || 0) / mins * 90;

    const STAT_KEYS: Record<string, { label: string, key: string, avgKey: string }> = {
      G90: { label: "Bàn thắng / 90'", key: 'goals', avgKey: 'goals' },
      xG90: { label: "Bàn thắng kỳ vọng (xG) / 90'", key: 'xG', avgKey: 'xg' },
      Sh90: { label: "Dứt điểm / 90'", key: 'shots', avgKey: 'shots' },
      A90: { label: "Kiến tạo / 90'", key: 'assists', avgKey: 'assists' },
      xA90: { label: "Kiến tạo kỳ vọng (xA) / 90'", key: 'xA', avgKey: 'xa' },
      KP90: { label: "Cơ hội tạo ra (KP) / 90'", key: 'key_passes', avgKey: 'key_passes' },
      xGC90: { label: "Chuỗi xG (xGChain) / 90'", key: 'xGChain', avgKey: 'xgchain' },
      xGB90: { label: "Phát triển bóng (xGBuildup) / 90'", key: 'xGBuildup', avgKey: 'xgbuildup' },
    };

    return Object.keys(STAT_KEYS).map(k => {
      const config = STAT_KEYS[k];
      const raw = per90(stats[config.key] || 0);
      const avg = positionAvg[config.avgKey] || 0.001;
      
      // Calculate normalized value: 50 = Average, 100 = 2x Average
      const ratio = raw / avg;
      const normalized = Math.min(110, ratio * 50);

      return {
        subject: k,
        fullLabel: config.label,
        value: normalized,
        rawValue: raw.toFixed(2),
        avgValue: avg.toFixed(2),
      };
    });
  }, [data, positionAvg]);

  const tableStats = useMemo(() => {
    if (!data || !data.stats) return [];
    const s = data.stats;
    const m = s.minutes || 1;
    const p90 = (v: number) => ((v || 0) / m * 90).toFixed(2);

    return [{
      key: '1',
      season: '2023/2024',
      team: data.original_club || data.club,
      apps: s.matches,
      min: s.minutes,
      g: s.goals,
      a: s.assists,
      sh90: p90(s.shots),
      kp90: p90(s.key_passes),
      xg: (s.xG || 0).toFixed(2),
      xa: (s.xA || 0).toFixed(2),
      xg90: p90(s.xG),
      xa90: p90(s.xA),
    }];
  }, [data]);

  const columns = [
    { title: 'Câu lạc bộ', dataIndex: 'team', key: 'team' },
    { title: 'Trận', dataIndex: 'apps', key: 'apps', align: 'right' as const },
    { title: 'Phút', dataIndex: 'min', key: 'min', align: 'right' as const },
    { title: 'Bàn thắng', dataIndex: 'g', key: 'g', align: 'right' as const },
    { title: 'Kiến tạo', dataIndex: 'a', key: 'a', align: 'right' as const },
    { title: 'Sh90', dataIndex: 'sh90', key: 'sh90', align: 'right' as const },
    { title: 'KP90', dataIndex: 'kp90', key: 'kp90', align: 'right' as const },
    { title: 'xG', dataIndex: 'xg', key: 'xg', align: 'right' as const, render: (v: any) => <Text strong style={{ color: '#52c41a' }}>{v}</Text> },
    { title: 'xA', dataIndex: 'xa', key: 'xa', align: 'right' as const, render: (v: any) => <Text strong style={{ color: '#52c41a' }}>{v}</Text> },
    { title: 'xG90', dataIndex: 'xg90', key: 'xg90', align: 'right' as const },
    { title: 'xA90', dataIndex: 'xa90', key: 'xa90', align: 'right' as const },
  ];

  if (loading) return <div style={{ textAlign: 'center', marginTop: 100 }}><Spin size="large" /></div>;
  if (!data) return <Title level={3}>Cầu thủ không tồn tại</Title>;

  return (
    <div style={{ paddingBottom: 40 }}>
      <Row gutter={[24, 24]}>
        {/* Left Section: Radar & Stats Table */}
        <Col xs={24} lg={17}>
          <Space direction="vertical" style={{ width: '100%' }} size={24}>
            <Row gutter={24}>
              <Col span={12}>
                <Card title="Thông số (trên 90 phút)" size="small" bordered={false} className="stat-card">
                  <div style={{ width: '100%', height: 350 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                        <PolarGrid stroke="#e8e8e8" />
                        <PolarAngleAxis dataKey="subject" tick={{ fill: '#8c8c8c', fontSize: 12 }} />
                        <PolarRadiusAxis angle={30} domain={[0, 100]} axisLine={false} tick={false} />
                        <Radar
                          name={data.name}
                          dataKey="value"
                          stroke="#1677ff"
                          fill="#1677ff"
                          fillOpacity={0.4}
                        />
                        <RechartsTooltip
                          content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                              const item = payload[0].payload;
                              return (
                                <div style={{ background: '#fff', padding: '8px 12px', border: '1px solid #f0f0f0', borderRadius: 4, boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
                                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{item.fullLabel}</div>
                                  <div style={{ color: '#1677ff', fontSize: 14 }}>
                                    Của cầu thủ: <span style={{ fontWeight: 700 }}>{item.rawValue}</span>
                                  </div>
                                  <div style={{ color: '#8c8c8c', fontSize: 13 }}>
                                    Trung bình vị trí: <span style={{ fontWeight: 500 }}>{item.avgValue}</span>
                                  </div>
                                </div>
                              );
                            }
                            return null;
                          }}
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              </Col>
              <Col span={12}>
                <Card title="Thông tin cơ bản" size="small" bordered={false} className="stat-card" style={{ height: '100%' }}>
                  <Descriptions column={1} bordered size="small">
                    <Descriptions.Item label="Tên cầu thủ"><Text strong style={{ fontSize: 18 }}>{data.name}</Text></Descriptions.Item>
                    <Descriptions.Item label="Vị trí"><Tag color="blue" style={{ fontWeight: 600 }}>{data.position}</Tag></Descriptions.Item>
                    <Descriptions.Item label="Giải đấu">{formatLeague(data.league)}</Descriptions.Item>
                    <Descriptions.Item label="Câu lạc bộ">{data.club}</Descriptions.Item>
                    <Descriptions.Item label="Định giá"><Text strong style={{ color: '#389e0d' }}>{formatMoney(data.market_value)}</Text></Descriptions.Item>
                    <Descriptions.Item label="Độ tuổi">{data.age || 'N/A'}</Descriptions.Item>
                    <Descriptions.Item label="Chiều cao">{data.height ? `${data.height} cm` : 'N/A'}</Descriptions.Item>
                    <Descriptions.Item label="Chân thuận">
                      {data.foot?.toLowerCase() === 'left' ? 'Trái' :
                        data.foot?.toLowerCase() === 'right' ? 'Phải' :
                          data.foot?.toLowerCase() === 'both' ? 'Cả hai' :
                            data.foot || 'N/A'}
                    </Descriptions.Item>
                    <Descriptions.Item label="Số trận">{data.stats.matches}</Descriptions.Item>
                  </Descriptions>
                </Card>
              </Col>
            </Row>

            <Card title="Thống kê chi tiết (mùa giải 2025/2026)" size="small" bordered={false} className="stat-card">
              <Table
                columns={columns}
                dataSource={tableStats}
                pagination={false}
                size="small"
                bordered
                className="understat-table"
              />
            </Card>
          </Space>
        </Col>

        {/* Right Section: Auction & Negotiation */}
        <Col xs={24} lg={7}>
          <Space direction="vertical" style={{ width: '100%' }} size={16}>
            {data.club === myClub ? (
              <Card bordered={false} className="stat-card" style={{ textAlign: 'center', background: '#f6ffed', border: '1px solid #b7eb8f' }}>
                <TrophyOutlined style={{ fontSize: 24, color: '#52c41a', marginBottom: 12 }} />
                <Title level={5} style={{ margin: 0, color: '#52c41a' }}>Đây là cầu thủ của bạn</Title>
                <Text type="secondary">Bạn không thể thực hiện giao dịch với chính cầu thủ của mình.</Text>
              </Card>
            ) : (
              <>
                <Card
                  title={
                    <Space>
                      <MessageOutlined style={{ color: '#fa8c16' }} />
                      <span>Giao dịch trực tiếp</span>
                    </Space>
                  }
                  bordered={false}
                  className="stat-card"
                  style={{ background: '#fff7e6' }}
                >
                  <div style={{ textAlign: 'center', marginBottom: 16 }}>
                    <Text type="secondary">Bắt đầu phiên đàm phán bí mật với CLB chủ quản.</Text>
                  </div>
                  <Button
                    type="primary"
                    block
                    size="large"
                    icon={<MessageOutlined />}
                    loading={inquiring}
                    disabled={hasNego}
                    onClick={handleInquire}
                    style={{ 
                      height: 48, 
                      fontWeight: 600, 
                      background: hasNego ? '#d9d9d9' : '#fa8c16', 
                      borderColor: hasNego ? '#d9d9d9' : '#fa8c16' 
                    }}
                  >
                    {hasNego ? 'ĐÃ GỬI YÊU CẦU ĐÀM PHÁN' : 'HỎI MUA (ĐÀM PHÁN)'}
                  </Button>
                </Card>
              </>
            )}
          </Space>
        </Col>
      </Row>

      <style jsx global>{`
        .stat-card {
          box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px 0 rgba(0, 0, 0, 0.02);
          border-radius: 8px;
        }
        .understat-table .ant-table-thead > tr > th {
          background: #fafafa;
          font-weight: 600;
          font-size: 12px;
          padding: 8px !important;
        }
        .understat-table .ant-table-tbody > tr > td {
          font-size: 13px;
          padding: 8px !important;
        }
        .custom-bid-input .ant-input-number-input {
          font-weight: 700;
          color: #1677ff;
          font-size: 18px;
          padding-right: 30px !important;
        }
      `}</style>
    </div>
  );
}

function Breadcrumb({ items }: { items: { title: string }[] }) {
  return (
    <div style={{ fontSize: 13, color: '#8c8c8c' }}>
      {items.map((item, i) => (
        <span key={i}>
          {item.title}
          {i < items.length - 1 && <span style={{ margin: '0 8px' }}>/</span>}
        </span>
      ))}
    </div>
  );
}
