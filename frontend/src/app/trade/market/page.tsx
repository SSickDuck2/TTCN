'use client';
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Table, Tag, Input, Typography, Card, Button, App,
  Select, Slider, Row, Col, Space, Divider, Badge, Spin,
  InputNumber, Tooltip, Pagination,
} from 'antd';
import {
  SearchOutlined, FilterOutlined, ClearOutlined, ReloadOutlined,
  RiseOutlined, TeamOutlined,
} from '@ant-design/icons';
import { fetchApi } from '@/libs/api';
import { useRouter } from 'next/navigation';

const { Title, Text } = Typography;
const { Option } = Select;

const LEAGUES = ['Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1'];
const POSITIONS = ['GK', 'DF', 'MF', 'FW'];
const POSITION_COLORS: Record<string, string> = {
  GK: 'gold', DF: 'blue', MF: 'green', FW: 'red',
};
const POSITION_LABELS: Record<string, string> = {
  GK: 'Thủ môn', DF: 'Hậu vệ', MF: 'Tiền vệ', FW: 'Tiền đạo',
};

interface Player {
  player_id: number;
  listing_id: number;
  name: string;
  position: string;
  market_value: number;
  club: string;
  league: string;
  weekly_wage: number;
}

interface Filters {
  name: string;
  position: string | null;
  league: string | null;
  club: string | null;
  minPrice: number | null;
  maxPrice: number | null;
  minAge: number;
  maxAge: number;
}

const DEFAULT_FILTERS: Filters = {
  name: '',
  position: null,
  league: null,
  club: null,
  minPrice: null,
  maxPrice: null,
  minAge: 15,
  maxAge: 60,
};

const PAGE_SIZE = 100;

function formatMoney(value: number) {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
  return `${value.toFixed(0)}`;
}

export default function Market() {
  const router = useRouter();
  const { message } = App.useApp();

  const [players, setPlayers] = useState<Player[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [clubs, setClubs] = useState<string[]>([]);
  const [clubsLoading, setClubsLoading] = useState(false);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [pendingFilters, setPendingFilters] = useState<Filters>(DEFAULT_FILTERS);
  const searchRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const buildParams = useCallback((f: Filters, pg: number) => {
    const params = new URLSearchParams();
    params.set('page', String(pg));
    params.set('page_size', String(PAGE_SIZE));
    if (f.name) params.set('name', f.name);
    if (f.position) params.set('position', f.position);
    if (f.league) params.set('league', f.league);
    if (f.club) params.set('club', f.club);
    if (f.minPrice !== null && f.minPrice >= 0) params.set('min_price', String(f.minPrice));
    if (f.maxPrice !== null) params.set('max_price', String(f.maxPrice));
    if (f.minAge !== DEFAULT_FILTERS.minAge) params.set('min_age', String(f.minAge));
    if (f.maxAge !== DEFAULT_FILTERS.maxAge) params.set('max_age', String(f.maxAge));
    return params.toString();
  }, []);

  const loadPlayers = useCallback(async (f: Filters, pg: number) => {
    setLoading(true);
    try {
      const qs = buildParams(f, pg);
      const res = await fetchApi(`/market/players?${qs}`);
      setPlayers(res.players);
      setTotal(res.total);
    } catch {
      message.error('Lỗi khi tải dữ liệu thị trường');
    } finally {
      setLoading(false);
    }
  }, [buildParams, message]);

  const loadClubs = useCallback(async (league: string) => {
    setClubsLoading(true);
    try {
      const res = await fetchApi(`/market/clubs?league=${encodeURIComponent(league)}`);
      setClubs(res);
    } catch {
      setClubs([]);
    } finally {
      setClubsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPlayers(DEFAULT_FILTERS, 1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const applyFilters = () => {
    setFilters(pendingFilters);
    setPage(1);
    loadPlayers(pendingFilters, 1);
  };

  const resetFilters = () => {
    setPendingFilters(DEFAULT_FILTERS);
    setFilters(DEFAULT_FILTERS);
    setClubs([]);
    setPage(1);
    loadPlayers(DEFAULT_FILTERS, 1);
  };

  const handleLeagueChange = (val: string | null) => {
    setPendingFilters((f) => ({ ...f, league: val ?? null, club: null }));
    if (val) loadClubs(val);
    else setClubs([]);
  };

  const handlePageChange = (pg: number) => {
    setPage(pg);
    loadPlayers(filters, pg);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleNameSearch = (val: string) => {
    setPendingFilters((f) => ({ ...f, name: val }));
    if (searchRef.current) clearTimeout(searchRef.current);
    searchRef.current = setTimeout(() => {
      const newF = { ...pendingFilters, name: val };
      setFilters(newF);
      setPage(1);
      loadPlayers(newF, 1);
    }, 500);
  };

  const isFiltered =
    !!pendingFilters.position ||
    !!pendingFilters.league ||
    !!pendingFilters.club ||
    pendingFilters.minPrice !== null ||
    pendingFilters.maxPrice !== null ||
    pendingFilters.minAge !== DEFAULT_FILTERS.minAge ||
    pendingFilters.maxAge !== DEFAULT_FILTERS.maxAge ||
    !!pendingFilters.name;

  const columns = [
    {
      title: '#',
      key: 'index',
      width: 48,
      render: (_: any, __: any, idx: number) => (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {(page - 1) * PAGE_SIZE + idx + 1}
        </Text>
      ),
    },
    {
      title: 'Cầu thủ',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (text: string, record: Player) => (
        <a
          onClick={() => router.push(`/trade/player/${record.player_id}`)}
          style={{ fontWeight: 600, color: '#1677ff', cursor: 'pointer' }}
        >
          {text}
        </a>
      ),
    },
    {
      title: 'Vị trí',
      dataIndex: 'position',
      key: 'position',
      width: 72,
      align: 'center' as const,
      render: (pos: string) => (
        <Tag color={POSITION_COLORS[pos] || 'default'} style={{ fontWeight: 600, margin: 0 }}>
          {pos}
        </Tag>
      ),
    },
    {
      title: 'Câu lạc bộ',
      dataIndex: 'club',
      key: 'club',
      ellipsis: true,
      render: (club: string) => <Text>{club}</Text>,
    },
    {
      title: 'Giải đấu',
      dataIndex: 'league',
      key: 'league',
      width: 130,
      ellipsis: true,
      render: (league: string) => <Text>{league}</Text>,
    },
    {
      title: 'Định giá (EUR)',
      dataIndex: 'market_value',
      key: 'market_value',
      width: 130,
      align: 'right' as const,
      sorter: (a: Player, b: Player) => a.market_value - b.market_value,
      defaultSortOrder: 'descend' as const,
      render: (val: number) => (
        <Text strong style={{ color: '#389e0d' }}>
          {formatMoney(val)}
        </Text>
      ),
    },
    {
      title: 'Hành động',
      key: 'action',
      width: 100,
      align: 'center' as const,
      render: (_: any, record: Player) => (
        <Button
          type="primary"
          size="small"
          onClick={() => router.push(`/trade/player/${record.player_id}`)}
        >
          Chi tiết
        </Button>
      ),
    },
  ];

  return (
    <div style={{ paddingBottom: 40 }}>
      {/* Page Header */}
      <div
        style={{
          background: '#f8f9fa',
          borderBottom: '2px solid #1677ff',
          padding: '20px 0',
          marginBottom: 20,
          marginLeft: -48,
          marginRight: -48,
          marginTop: -24,
          paddingLeft: 48,
          paddingRight: 48,
        }}
      >
        <Title level={3} style={{ margin: 0, color: '#1677ff' }}>
          Thị trường chuyển nhượng
        </Title>
      </div>

      <Row gutter={[16, 16]} align="top">
        {/* Filter Panel */}
        <Col xs={24} lg={5}>
          <Card
            size="small"
            title={
              <Space size={6}>
                <FilterOutlined style={{ color: '#1677ff' }} />
                <span style={{ fontWeight: 600 }}>Bộ lọc</span>
                {isFiltered && <Badge dot />}
              </Space>
            }
            extra={
              <Tooltip title="Xóa tất cả bộ lọc">
                <Button
                  size="small"
                  type="text"
                  icon={<ClearOutlined />}
                  onClick={resetFilters}
                  disabled={!isFiltered}
                />
              </Tooltip>
            }
            style={{ borderRadius: 8, position: 'sticky', top: 72 }}
            bodyStyle={{ padding: '12px 16px' }}
          >
            <Space direction="vertical" style={{ width: '100%' }} size={12}>
              {/* Name search */}
              <div>
                <Text type="secondary" style={{ display: 'block', marginBottom: 4, fontSize: 12 }}>
                  Tìm kiếm
                </Text>
                <Input
                  prefix={<SearchOutlined style={{ color: '#bbb' }} />}
                  placeholder="Tên cầu thủ..."
                  value={pendingFilters.name}
                  onChange={(e) => handleNameSearch(e.target.value)}
                  allowClear
                  size="small"
                />
              </div>

              <Divider style={{ margin: '2px 0' }} />

              {/* Position */}
              <div>
                <Text type="secondary" style={{ display: 'block', marginBottom: 4, fontSize: 12 }}>
                  Vị trí
                </Text>
                <Select
                  style={{ width: '100%' }}
                  placeholder="Tất cả"
                  allowClear
                  size="small"
                  value={pendingFilters.position}
                  onChange={(val) => setPendingFilters((f) => ({ ...f, position: val ?? null }))}
                >
                  {POSITIONS.map((p) => (
                    <Option key={p} value={p}>
                      <Tag color={POSITION_COLORS[p]} style={{ marginRight: 4, fontSize: 11 }}>{p}</Tag>
                      {POSITION_LABELS[p]}
                    </Option>
                  ))}
                </Select>
              </div>

              {/* League */}
              <div>
                <Text type="secondary" style={{ display: 'block', marginBottom: 4, fontSize: 12 }}>
                  Giải đấu
                </Text>
                <Select
                  style={{ width: '100%' }}
                  placeholder="Tất cả"
                  allowClear
                  size="small"
                  value={pendingFilters.league}
                  onChange={handleLeagueChange}
                >
                  {LEAGUES.map((l) => (
                    <Option key={l} value={l}>{l}</Option>
                  ))}
                </Select>
              </div>

              {/* Club */}
              <div>
                <Text type="secondary" style={{ display: 'block', marginBottom: 4, fontSize: 12 }}>
                  Câu lạc bộ
                </Text>
                <Tooltip title={!pendingFilters.league ? 'Chọn giải đấu trước' : ''}>
                  <Select
                    style={{ width: '100%' }}
                    placeholder={pendingFilters.league ? 'Chọn CLB...' : 'Chưa chọn giải'}
                    allowClear
                    size="small"
                    disabled={!pendingFilters.league}
                    loading={clubsLoading}
                    value={pendingFilters.club}
                    onChange={(val) => setPendingFilters((f) => ({ ...f, club: val ?? null }))}
                    showSearch
                    optionFilterProp="children"
                  >
                    {clubs.map((c) => (
                      <Option key={c} value={c}>{c}</Option>
                    ))}
                  </Select>
                </Tooltip>
              </div>

              <Divider style={{ margin: '2px 0' }} />

              {/* Price */}
              <div>
                <Text type="secondary" style={{ display: 'block', marginBottom: 4, fontSize: 12 }}>
                  Định giá (triệu EUR)
                </Text>
                <Row gutter={6}>
                  <Col span={12}>
                    <InputNumber
                      style={{ width: '100%' }}
                      placeholder="Từ"
                      min={0}
                      size="small"
                      value={pendingFilters.minPrice ?? undefined}
                      onChange={(val) =>
                        setPendingFilters((f) => ({
                          ...f,
                          minPrice: val !== null && val !== undefined ? Number(val) : null,
                        }))
                      }
                    />
                  </Col>
                  <Col span={12}>
                    <InputNumber
                      style={{ width: '100%' }}
                      placeholder="Đến"
                      min={0}
                      size="small"
                      value={pendingFilters.maxPrice ?? undefined}
                      onChange={(val) =>
                        setPendingFilters((f) => ({
                          ...f,
                          maxPrice: val !== null && val !== undefined ? Number(val) : null,
                        }))
                      }
                    />
                  </Col>
                </Row>
              </div>

              {/* Age */}
              <div>
                <Text type="secondary" style={{ display: 'block', marginBottom: 4, fontSize: 12 }}>
                  Độ tuổi: {pendingFilters.minAge} – {pendingFilters.maxAge}
                </Text>
                <Slider
                  range
                  min={15}
                  max={60}
                  value={[pendingFilters.minAge, pendingFilters.maxAge]}
                  onChange={(val: number[]) =>
                    setPendingFilters((f) => ({ ...f, minAge: val[0], maxAge: val[1] }))
                  }
                  marks={{ 15: '15', 30: '30', 45: '45', 60: '60' }}
                  style={{ marginBottom: 24 }}
                />
              </div>

              <Button
                type="primary"
                block
                size="middle"
                icon={<SearchOutlined />}
                onClick={applyFilters}
              >
                Áp dụng
              </Button>
            </Space>
          </Card>
        </Col>

        {/* Player Table */}
        <Col xs={24} lg={19}>
          <Card
            size="small"
            style={{ borderRadius: 8 }}
            title={
              <Space size={8}>
                <Text strong>Danh sách cầu thủ</Text>
                {!loading && (
                  <Badge
                    count={total}
                    overflowCount={9999}
                    style={{ backgroundColor: '#1677ff' }}
                  />
                )}
              </Space>
            }
            extra={
              <Button
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => loadPlayers(filters, page)}
                loading={loading}
              >
                Làm mới
              </Button>
            }
            bodyStyle={{ padding: '0 0 12px 0' }}
          >
            <Spin spinning={loading} tip="Đang tải...">
              <Table
                columns={columns}
                dataSource={players}
                rowKey="player_id"
                loading={false}
                pagination={false}
                size="small"
                tableLayout="fixed"
                locale={{ emptyText: 'Không tìm thấy cầu thủ nào' }}
                style={{ fontSize: 13 }}
                rowClassName={(_, idx) => (idx % 2 === 0 ? 'row-even' : 'row-odd')}
              />
            </Spin>

            {total > 0 && (
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 16px 0',
                  borderTop: '1px solid #f0f0f0',
                  marginTop: 4,
                }}
              >
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {Math.min((page - 1) * PAGE_SIZE + 1, total)}–{Math.min(page * PAGE_SIZE, total)} / {total} cau thu
                </Text>
                <Pagination
                  current={page}
                  total={total}
                  pageSize={PAGE_SIZE}
                  onChange={handlePageChange}
                  showSizeChanger={false}
                  showQuickJumper
                  size="small"
                />
              </div>
            )}
          </Card>
        </Col>
      </Row>

      <style>{`
        .row-even td { background: #fff; }
        .row-odd  td { background: #fafafa; }
        .ant-table-tbody > tr:hover > td { background: #e6f4ff !important; }
        .ant-table-cell { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      `}</style>
    </div>
  );
}
