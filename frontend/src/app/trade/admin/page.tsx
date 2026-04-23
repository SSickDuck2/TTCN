'use client';

import React, { useState, useEffect } from 'react';
import { Typography, Card, Row, Col, Button, Statistic, Space, Divider, message, Popconfirm, Select, InputNumber } from 'antd';
import { 
  SettingOutlined, ClockCircleOutlined, RobotOutlined, 
  ThunderboltOutlined, WarningOutlined, DatabaseOutlined, ReloadOutlined
} from '@ant-design/icons';
import { 
  adminSetState, adminAdvanceTime, adminTriggerSimulation, 
  adminResetData, adminSystemHealth, getTimeStatus 
} from '@/libs/api';

const { Title, Text, Paragraph } = Typography;

export default function AdminDashboardPage() {
  const [health, setHealth] = useState<any>(null);
  const [timeState, setTimeState] = useState<any>(null);
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [loadingAction, setLoadingAction] = useState(false);
  
  const [targetState, setTargetState] = useState('TRANSFER_OPEN');
  const [advanceDays, setAdvanceDays] = useState(1);

  const fetchHealth = async () => {
    setLoadingHealth(true);
    try {
      const data = await adminSystemHealth();
      setHealth(data);
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

  useEffect(() => {
    fetchHealth();
    fetchTime();
    
    // Refresh time every 10s
    const timer = setInterval(fetchTime, 10000);
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

  const handleResetData = async () => {
    setLoadingAction(true);
    try {
      await adminResetData();
      message.success('Hệ thống đã được Reset về mặc định!');
      fetchHealth();
      fetchTime();
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
                <Text type="secondary">Trạng thái hiện tại:</Text><br/>
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

        {/* Simulation */}
        <Col xs={24} md={12}>
          <Card title={<><RobotOutlined /> AI Simulation</>} bordered={false}>
            <Paragraph>
              Bình thường Bot sẽ chạy ngầm định kỳ. Sử dụng nút này để ép các Bot của máy thực hiện đánh giá thị trường, gửi Inquiry và trả giá ngay lập tức.
            </Paragraph>
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
              <li>Đưa ngày hệ thống về 01/06/2024</li>
              <li>Mở cửa thị trường (TRANSFER_OPEN)</li>
              <li>Xóa SẠCH các phiên đàm phán, lượt bid đấu giá</li>
              <li>Khôi phục Ngân sách của toàn bộ các Câu lạc bộ về 100 Triệu Euro</li>
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
