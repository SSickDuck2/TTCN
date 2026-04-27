'use client';

import React, { useState, useEffect } from 'react';
import { Typography, Card, Row, Col, Button, Statistic, Space, Divider, message, Popconfirm, Select, InputNumber, Table, Tag, Switch } from 'antd';
import {
  SettingOutlined, ClockCircleOutlined, RobotOutlined,
  ThunderboltOutlined, WarningOutlined, DatabaseOutlined, ReloadOutlined,
  MessageOutlined
} from '@ant-design/icons';
import {
  adminSetState, adminAdvanceTime, adminTriggerSimulation,
  adminResetData, adminSystemHealth, getTimeStatus,
  adminGetAllNegotiations, adminCancelNegotiation,
  adminGetSimulationStatus, adminToggleSimulation, adminGetClubsInDebt
} from '@/libs/api';

import { useRouter } from 'next/navigation';
import { fetchApi } from '@/libs/api';

const { Title, Text, Paragraph } = Typography;

function formatM(v: number) {
  if (!v) return '—';
  return v >= 1_000_000 ? `€${(v / 1_000_000).toFixed(1)}M` : `€${(v / 1_000).toFixed(0)}K`;
}

export default function AdminDashboardPage() {
  const router = useRouter();
  const [health, setHealth] = useState<any>(null);
  const [timeState, setTimeState] = useState<any>(null);
  const [negotiations, setNegotiations] = useState<any[]>([]);
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [loadingNegos, setLoadingNegos] = useState(false);
  const [loadingAction, setLoadingAction] = useState(false);
  const [simulationEnabled, setSimulationEnabled] = useState(false);
  const [clubsInDebt, setClubsInDebt] = useState<any[]>([]);
  const [loadingClubsDebt, setLoadingClubsDebt] = useState(false);

  const [targetState, setTargetState] = useState('TRANSFER_OPEN');
  const [advanceDays, setAdvanceDays] = useState(1);

  const checkAdmin = async () => {
    try {
      const me = await fetchApi('/me');
      if (me.username !== 'admin') {
        router.push('/trade/market');
      }
    } catch {
      router.push('/');
    }
  };

  useEffect(() => {
    checkAdmin();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchNegotiations = async () => {
    setLoadingNegos(true);
    try {
      const data = await adminGetAllNegotiations();
      setNegotiations(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingNegos(false);
    }
  };

  const handleCancelNego = async (id: number) => {
    try {
      await adminCancelNegotiation(id);
      message.success('Đã hủy đàm phán');
      fetchNegotiations();
    } catch {
      message.error('Lỗi khi hủy đàm phán');
    }
  };

  const fetchClubsInDebt = async () => {
    setLoadingClubsDebt(true);
    try {
      const data = await adminGetClubsInDebt();
      setClubsInDebt(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingClubsDebt(false);
    }
  };

  const fetchHealth = async () => {
    setLoadingHealth(true);
    try {
      const data = await adminSystemHealth();
      setHealth(data);
      fetchClubsInDebt();
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingHealth(false);
    }
  };

  const fetchTime = async () => {
    try {
      const data = await getTimeStatus();
      setTimeState(data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchSimulationStatus = async () => {
    try {
      const data = await adminGetSimulationStatus();
      setSimulationEnabled(data.enabled);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchHealth();
    fetchTime();
    fetchNegotiations();
    fetchSimulationStatus();
    fetchClubsInDebt();

    // Refresh time every 10s
    const timer = setInterval(() => {
      fetchTime();
      fetchSimulationStatus();
    }, 10000);
    return () => clearInterval(timer);
  }, []);

  const handleSetState = async () => {
    setLoadingAction(true);
    try {
      await adminSetState(targetState);
      message.success('Cập nhật trạng thái thành công');
      fetchTime();
    } catch {
      message.error('Lỗi khi cập nhật trạng thái');
    } finally {
      setLoadingAction(false);
    }
  };

  const handleAdvanceTime = async () => {
    setLoadingAction(true);
    try {
      await adminAdvanceTime(advanceDays);
      message.success(`Đã qua nhanh ${advanceDays} ngày`);
      fetchTime();
    } catch {
      message.error('Lỗi khi qua ngày');
    } finally {
      setLoadingAction(false);
    }
  };

  const handleTriggerSimulation = async () => {
    setLoadingAction(true);
    try {
      await adminTriggerSimulation();
      message.success('Đã kích hoạt Simulation Cycle');
    } catch {
      message.error('Lỗi chạy Simulation');
    } finally {
      setLoadingAction(false);
    }
  };

  const handleToggleSimulation = async () => {
    try {
      const data = await adminToggleSimulation();
      setSimulationEnabled(data.enabled);
      message.success(`Đã ${data.enabled ? 'bật' : 'tắt'} Chế độ Tự động`);
    } catch {
      message.error('Lỗi khi thay đổi trạng thái Chế độ Tự động');
    }
  };

  const handleResetData = async () => {
    setLoadingAction(true);
    try {
      await adminResetData();
      message.success('Hệ thống đã được Reset về mặc định!');
      fetchHealth();
      fetchTime();
      fetchSimulationStatus();
    } catch {
      message.error('Lỗi khi Reset Data');
    } finally {
      setLoadingAction(false);
    }
  };

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '24px 0' }}>
      <Title level={2}>
        <SettingOutlined /> Admin Dashboard
      </Title>
      <Paragraph type="secondary">
        Công cụ quản trị hệ thống, kiểm soát thời gian game và mô phỏng thị trường.
      </Paragraph>

      <Row gutter={[16, 16]}>
        {/* System Health */}
        <Col xs={24} md={12}>
          <Card title={<><DatabaseOutlined /> Sức Khỏe Hệ Thống</>} bordered={false} extra={<Button icon={<ReloadOutlined />} onClick={fetchHealth} loading={loadingHealth}>Làm mới</Button>}>
            <Row gutter={16}>
              <Col span={8}>
                <Statistic title="Tổng CLB" value={health?.total_clubs ?? '-'} />
              </Col>
              <Col span={8}>
                <Statistic title="Tổng Hợp đồng" value={health?.total_contracts ?? '-'} />
              </Col>
              <Col span={8}>
                <Statistic
                  title="CLB nợ ngân sách"
                  value={health?.clubs_in_debt ?? '-'}
                  valueStyle={{ color: health?.clubs_in_debt > 0 ? '#cf1322' : '#3f8600' }}
                />
              </Col>
            </Row>
          </Card>
        </Col>

        {/* Time Control */}
        <Col xs={24} md={12}>
          <Card title={<><ClockCircleOutlined /> Điều Khiển Thời Gian</>} bordered={false}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ background: '#f5f5f5', padding: '12px', borderRadius: 8 }}>
                <Text type="secondary">Trạng thái hiện tại:</Text><br />
                <Text strong style={{ fontSize: 18 }}>{timeState ? new Date(timeState.current_date).toLocaleDateString('vi-VN') : '...'}</Text>
                <Divider type="vertical" />
                <Text strong color="blue">{timeState?.current_state}</Text>
              </div>

              <Space>
                <Select value={targetState} onChange={setTargetState} style={{ width: 180 }}>
                  <Select.Option value="TRANSFER_OPEN">TRANSFER_OPEN</Select.Option>
                  <Select.Option value="TRANSFER_CLOSED">TRANSFER_CLOSED</Select.Option>
                  <Select.Option value="SEASON_UPDATE">SEASON_UPDATE</Select.Option>
                  <Select.Option value="OFF_SEASON">OFF_SEASON</Select.Option>
                </Select>
                <Button type="primary" onClick={handleSetState} loading={loadingAction}>Ép Trạng Thái</Button>
              </Space>

              <Space style={{ marginTop: 16 }}>
                <InputNumber min={1} max={365} value={advanceDays} onChange={v => setAdvanceDays(v || 1)} addonAfter="Ngày" />
                <Button onClick={handleAdvanceTime} loading={loadingAction}>Tua nhanh thời gian</Button>
              </Space>
            </Space>
          </Card>
        </Col>

        {/* Negotiation Management */}
        <Col span={24}>
          <Card title={<><MessageOutlined /> Nhật ký Đàm phán</>} bordered={false} extra={<Button icon={<ReloadOutlined />} onClick={fetchNegotiations} loading={loadingNegos}>Làm mới</Button>}>
            <Table
              dataSource={negotiations}
              pagination={{ pageSize: 5 }}
              size="small"
              columns={[
                { title: 'Cầu thủ', dataIndex: 'player_name', key: 'player' },
                { title: 'Bên mua', dataIndex: 'buyer_name', key: 'buyer' },
                { title: 'Bên bán', dataIndex: 'seller_name', key: 'seller' },
                {
                  title: 'Trạng thái',
                  dataIndex: 'status',
                  key: 'status',
                  render: (st: string) => <Tag color={st === 'ACCEPTED' ? 'green' : st === 'CANCELLED' ? 'gray' : 'orange'}>{st}</Tag>
                },
                {
                  title: 'Giá (Offer/Demand)',
                  key: 'price',
                  render: (_, r) => {
                    if (r.status === 'ACCEPTED') {
                      return <Text strong style={{ color: '#52c41a' }}>{formatM(r.current_offer)}</Text>;
                    }
                    return <Text>{formatM(r.current_offer)} / {formatM(r.demand)}</Text>;
                  }
                },
                {
                  title: 'Hành động',
                  key: 'action',
                  render: (_, r) => (
                    r.status !== 'CANCELLED' && r.status !== 'ACCEPTED' && (
                      <Popconfirm title="Admin hủy đàm phán này?" onConfirm={() => handleCancelNego(r.id)}>
                        <Button type="link" danger icon={<WarningOutlined />}>Hủy</Button>
                      </Popconfirm>
                    )
                  )
                }
              ]}
            />
          </Card>
        </Col>

        {/* Clubs in Debt / Banned List */}
        <Col span={24}>
          <Card title={<><WarningOutlined style={{ color: '#faad14' }} /> Danh sách CLB nợ / Cấm chuyển nhượng</>} bordered={false} extra={<Button icon={<ReloadOutlined />} onClick={fetchClubsInDebt} loading={loadingClubsDebt}>Làm mới</Button>}>
            <Table
              dataSource={clubsInDebt}
              pagination={{ pageSize: 5 }}
              size="small"
              columns={[
                { title: 'Câu lạc bộ', dataIndex: 'name', key: 'name' },
                { 
                  title: 'Ngân sách hiện tại', 
                  dataIndex: 'budget', 
                  key: 'budget',
                  render: (v: number) => <Text type={v < 0 ? 'danger' : 'success'}>{formatM(v)}</Text>
                },
                { 
                  title: 'Trạng thái cấm', 
                  dataIndex: 'is_banned', 
                  key: 'is_banned',
                  render: (b: boolean) => b ? <Tag color="error">BỊ CẤM</Tag> : <Tag color="success">BÌNH THƯỜNG</Tag>
                }
              ]}
            />
          </Card>
        </Col>

        {/* Simulation */}
        <Col xs={24} md={12}>
          <Card title={<><RobotOutlined /> Mô phỏng Tự động (Simulation)</>} bordered={false}>
            <Paragraph>
              Bật công tắc dưới đây để hệ thống tự động đánh giá thị trường, gửi Inquiry và trả giá ngầm định kỳ. Bạn cũng có thể dùng nút Trigger để ép chạy ngay lập tức.
            </Paragraph>
            <Space size="large" align="center" style={{ marginBottom: 16 }}>
              <Space>
                <Text strong>Trạng thái Tự động:</Text>
                <Switch
                  checked={simulationEnabled}
                  onChange={handleToggleSimulation}
                  checkedChildren="Đang chạy"
                  unCheckedChildren="Đang tắt"
                />
              </Space>
            </Space>
            <br />
            <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleTriggerSimulation} loading={loadingAction}>
              Trigger Simulation Now
            </Button>
          </Card>
        </Col>

        {/* Danger Zone */}
        <Col xs={24} md={12}>
          <Card title={<><WarningOutlined style={{ color: 'red' }} /> Danger Zone</>} bordered={false} style={{ borderColor: '#ffccc7', background: '#fff1f0' }}>
            <Paragraph strong style={{ color: '#cf1322' }}>
              Hành động này sẽ:
            </Paragraph>
            <ul>
              <li>Đưa ngày hệ thống về 01/06/2026</li>
              <li>Mở cửa thị trường (TRANSFER_OPEN)</li>
              <li>Xóa SẠCH các phiên đàm phán, lượt bid đấu giá</li>
            </ul>
            <Popconfirm
              title="Xác nhận Reset Hệ thống?"
              description="Toàn bộ lịch sử giao dịch sẽ mất vĩnh viễn."
              onConfirm={handleResetData}
              okText="Reset Ngay"
              cancelText="Hủy"
              okButtonProps={{ danger: true }}
            >
              <Button danger type="primary" loading={loadingAction} icon={<WarningOutlined />}>
                Khôi Phục Dữ Liệu Demo
              </Button>
            </Popconfirm>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
