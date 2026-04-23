'use client';
import { useEffect, useState } from 'react';
import { Tag, Tooltip, Space } from 'antd';
import { ClockCircleOutlined, LockOutlined, UnlockOutlined, SyncOutlined } from '@ant-design/icons';
import { getTimeStatus } from '@/libs/api';

interface TimeInfo {
  current_date: string;
  current_state: string;
  season_year: number;
}

const STATE_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode; description: string }> = {
  TRANSFER_OPEN: {
    label: 'TTCN Mở Cửa',
    color: 'success',
    icon: <UnlockOutlined />,
    description: 'Thị trường chuyển nhượng đang hoạt động. Bạn có thể Bid, Inquire và Quick Sell.',
  },
  TRANSFER_CLOSED: {
    label: 'TTCN Đóng Cửa',
    color: 'error',
    icon: <LockOutlined />,
    description: 'Cửa sổ chuyển nhượng đã đóng. Giao dịch bị tạm khoá.',
  },
  SEASON_UPDATE: {
    label: 'Cập Nhật Mùa',
    color: 'processing',
    icon: <SyncOutlined spin />,
    description: 'Hệ thống đang xử lý kết thúc mùa giải. Vui lòng chờ...',
  },
  OFF_SEASON: {
    label: 'Nghỉ Hè',
    color: 'warning',
    icon: <ClockCircleOutlined />,
    description: 'Mùa giải kết thúc. Chuẩn bị bước vào cửa sổ chuyển nhượng.',
  },
};

export default function TimeStatusBar() {
  const [timeInfo, setTimeInfo] = useState<TimeInfo | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getTimeStatus();
        setTimeInfo(data);
      } catch {
        // Lỗi kết nối → không hiển thị
      }
    };
    load();
    // Cập nhật mỗi 5 giây
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!timeInfo) return null;

  const stateConf = STATE_CONFIG[timeInfo.current_state] ?? {
    label: timeInfo.current_state,
    color: 'default',
    icon: <ClockCircleOutlined />,
    description: '',
  };

  const displayDate = timeInfo.current_date
    ? new Date(timeInfo.current_date).toLocaleDateString('vi-VN', {
        day: '2-digit', month: '2-digit', year: 'numeric',
      })
    : '—';

  return (
    <Space size={8} style={{ fontSize: 12 }}>
      <Tooltip title={stateConf.description}>
        <Tag
          icon={stateConf.icon}
          color={stateConf.color}
          style={{ margin: 0, cursor: 'help', fontWeight: 600 }}
        >
          {stateConf.label}
        </Tag>
      </Tooltip>
      <span style={{ color: '#888' }}>
        <ClockCircleOutlined style={{ marginRight: 4 }} />
        {displayDate}
      </span>
      <span style={{ color: '#aaa' }}>Mùa {timeInfo.season_year}/{timeInfo.season_year + 1}</span>
    </Space>
  );
}
