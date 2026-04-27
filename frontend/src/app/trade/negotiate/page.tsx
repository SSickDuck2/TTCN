'use client';
import { useEffect, useState, useCallback } from 'react';
import {
  Card, Typography, Tag, Button, App, Space, Divider, Slider,
  List, Modal, Badge, Empty, Spin, Row, Col, Statistic, Tooltip,
} from 'antd';
import {
  MessageOutlined, CheckOutlined, CloseOutlined,
  QuestionCircleOutlined, DollarOutlined, ArrowRightOutlined,
} from '@ant-design/icons';
import {
  getNegotiation, respondToInquiry, submitOffer,
  respondToOffer, cancelNegotiation, askNegotiationQuestion, getNegotiationQuestions,
} from '@/libs/api';
import { fetchApi } from '@/libs/api';

const { Title, Text, Paragraph } = Typography;

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  INQUIRY: { label: 'Chờ phản hồi', color: 'processing' },
  NEGOTIATING: { label: 'Đang đàm phán', color: 'warning' },
  ACCEPTED: { label: 'Thành công ✓', color: 'success' },
  REJECTED: { label: 'Bị từ chối', color: 'error' },
  CANCELLED: { label: 'Đã hủy', color: 'default' },
};

function formatM(v: number) {
  if (!v) return '—';
  return v >= 1_000_000 ? `€${(v / 1_000_000).toFixed(1)}M` : `€${(v / 1_000).toFixed(0)}K`;
}

function getPositionCategory(pos: string) {
  if (!pos) return 'Khác';
  const p = pos.toUpperCase();
  if (p.includes('FW')) return 'Tiền đạo (FW)';
  if (p.includes('MF')) return 'Tiền vệ (MF)';
  if (p.includes('DF')) return 'Hậu vệ (DF)';
  if (p.includes('GK')) return 'Thủ môn (GK)';
  return 'Khác';
}

export default function NegotiatePage() {
  const { message } = App.useApp();
  const [negotiations, setNegotiations] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [questions, setQuestions] = useState<Record<number, string>>({});
  const [activeNego, setActiveNego] = useState<any | null>(null);
  const [myClubId, setMyClubId] = useState<number | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [offerValue, setOfferValue] = useState(0);
  const [demandValue, setDemandValue] = useState(0);
  const [qaLog, setQaLog] = useState<{ q: string; a: string }[]>([]);
  const [actionLoading, setActionLoading] = useState(false);
  const [qaModalVisible, setQaModalVisible] = useState(false);

  const loadNegotiations = useCallback(async () => {
    setLoading(true);
    try {
      // Lấy tất cả negotiations của club hiện tại
      const res = await fetchApi('/negotiations/my');
      setNegotiations(res);
    } catch {
      message.error('Không thể tải danh sách đàm phán');
    } finally {
      setLoading(false);
    }
  }, [message]);

  const loadQuestions = useCallback(async () => {
    try {
      const res = await getNegotiationQuestions();
      setQuestions(res);
    } catch { /* ignore */ }
  }, []);

  const [clubInfo, setClubInfo] = useState<any>(null);

  const loadClub = useCallback(async () => {
    try {
      const res = await fetchApi('/me');
      setClubInfo(res);
      setMyClubId(res.id);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    loadNegotiations();
    loadQuestions();
    loadClub();
  }, [loadNegotiations, loadQuestions, loadClub]);

  const openNego = (nego: any) => {
    setActiveNego(nego);
    setOfferValue(nego.current_offer || Math.round(nego.market_value * 0.8));
    setDemandValue(nego.selling_club_demand || Math.round(nego.market_value * 1.2));
    setQaLog([]);
    setModalVisible(true);
  };

  const handleRespondInquiry = async (accept: boolean) => {
    if (!activeNego) return;
    setActionLoading(true);
    try {
      await respondToInquiry(activeNego.id, accept, accept ? demandValue : undefined);
      message.success(accept ? 'Đã đồng ý ngồi vào bàn đàm phán!' : 'Đã từ chối Inquiry.');
      setModalVisible(false);
      loadNegotiations();
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleSubmitOffer = async () => {
    if (!activeNego) return;
    setActionLoading(true);
    try {
      const res = await submitOffer(activeNego.id, offerValue);
      if (!res) return;
      if (res.error) {
        message.error(res.error);
        return;
      }
      if (res.status === 'ACCEPTED') message.success(`🎉 Deal thành công! Giá chốt: ${formatM(res.final_price)}`);
      else if (res.status === 'CANCELLED') message.warning('Đàm phán kết thúc — quá 3 hiệp.');
      else message.info('Đã gửi giá. Chờ đối phương phản hồi.');
      setActiveNego({ ...activeNego, ...res });
      loadNegotiations();
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCounter = async () => {
    if (!activeNego) return;
    setActionLoading(true);
    try {
      const res = await respondToOffer(activeNego.id, demandValue);
      if (!res) return;
      if (res.error) {
        message.error(res.error);
        return;
      }
      if (res.status === 'ACCEPTED') message.success(`🎉 Deal thành công!`);
      else if (res.status === 'CANCELLED') message.warning('Quá 3 hiệp — đàm phán kết thúc.');
      else message.info('Đã phản giá. Bên mua đang xem xét...');
      loadNegotiations();
      setModalVisible(false);
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleAskQuestion = async (qId: number) => {
    if (!activeNego) return;
    try {
      const res = await askNegotiationQuestion(activeNego.id, qId);
      if (res.error) { message.warning(res.error); return; }
      setQaLog(prev => [...prev, { q: res.question_text, a: res.answer }]);
      message.success(`Còn ${res.questions_remaining} câu hỏi trong hiệp này.`);
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleCancel = async () => {
    if (!activeNego) return;
    Modal.confirm({
      title: 'Xác nhận hủy đàm phán?',
      content: 'Hành động này không thể hoàn tác.',
      okText: 'Hủy đàm phán',
      okType: 'danger',
      cancelText: 'Giữ lại',
      onOk: async () => {
        try {
          await cancelNegotiation(activeNego.id);
          message.success('Đã hủy đàm phán.');
          setModalVisible(false);
          loadNegotiations();
        } catch (e: any) { message.error(e.message); }
      },
    });
  };

  return (
    <div style={{ paddingBottom: 40 }}>
      <div style={{ background: '#f8f9fa', borderBottom: '2px solid #1677ff', padding: '20px 0 20px 48px', marginBottom: 24, marginLeft: -48, marginRight: -48, marginTop: -24 }}>
        <Title level={3} style={{ margin: 0, color: '#1677ff' }}>
          <MessageOutlined style={{ marginRight: 8 }} />
          Phòng Đàm phán
        </Title>
        <Text type="secondary">Theo dõi và xử lý các thương vụ chuyển nhượng trực tiếp</Text>
      </div>

      <Spin spinning={loading}>
        {negotiations.length === 0 && !loading ? (
          <Empty description="Chưa có phiên đàm phán nào. Hãy gửi Inquiry từ trang Thị trường!" />
        ) : (
          ['Tiền đạo (FW)', 'Tiền vệ (MF)', 'Hậu vệ (DF)', 'Thủ môn (GK)', 'Khác'].map(category => {
            const categoryNegos = negotiations.filter(n => getPositionCategory(n.player_position) === category);
            if (categoryNegos.length === 0) return null;

            return (
              <div key={category} style={{ marginBottom: 32 }}>
                <Divider orientation="left">
                  <Text strong style={{ fontSize: 16 }}>{category}</Text>
                  <Tag color="blue" style={{ marginLeft: 8, borderRadius: 10 }}>{categoryNegos.length}</Tag>
                </Divider>
                <List
                  grid={{ gutter: 16, xs: 1, sm: 2, lg: 3 }}
                  dataSource={categoryNegos}
                  renderItem={(nego) => {
                    const conf = STATUS_CONFIG[nego.status] ?? { label: nego.status, color: 'default' };
                    return (
                      <List.Item>
                        <Card
                          hoverable
                          size="small"
                          style={{ borderRadius: 10 }}
                          onClick={() => openNego(nego)}
                          actions={[
                            <Tooltip title="Mở phiên đàm phán" key="open">
                              <Button type="link" icon={<ArrowRightOutlined />}>Chi tiết</Button>
                            </Tooltip>,
                          ]}
                        >
                          <Space direction="vertical" style={{ width: '100%' }}>
                            <Space justify="space-between" style={{ width: '100%' }}>
                              <Text strong ellipsis>{nego.player_name ?? `Player #${nego.player_id}`}</Text>
                              <Badge status={conf.color as any} text={conf.label} />
                            </Space>
                            <div style={{ marginTop: -4 }}>
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                {myClubId === nego.buying_club_id ? `Đối tác: ${nego.selling_club_name} (Bên bán)` : `Đối tác: ${nego.buying_club_name} (Bên mua)`}
                              </Text>
                            </div>
                            <Divider style={{ margin: '6px 0' }} />
                            <Row gutter={8}>
                              <Col span={12}>
                                <Statistic title={myClubId === nego.buying_club_id ? "Giá bạn bid" : "Giá đối phương bid"} value={nego.current_offer || 0} formatter={(v) => formatM(Number(v))} valueStyle={{ fontSize: 14, color: '#1677ff' }} />
                              </Col>
                              <Col span={12}>
                                <Statistic title={myClubId === nego.buying_club_id ? "Giá đối phương đòi" : "Giá bạn yêu cầu"} value={nego.selling_club_demand || 0} formatter={(v) => formatM(Number(v))} valueStyle={{ fontSize: 14, color: '#cf1322' }} />
                              </Col>
                            </Row>
                            <Space justify="space-between" style={{ width: '100%' }}>
                              <Text type="secondary" style={{ fontSize: 11 }}>Hiệp {nego.round_number}/3</Text>
                              {(nego.status === 'INQUIRY' || nego.status === 'NEGOTIATING') && nego.expires_in_days !== null && (
                                <Tag color={nego.expires_in_days <= 1 ? 'error' : 'warning'} style={{ margin: 0, fontSize: 11 }}>
                                  Hết hạn: {nego.expires_in_days} ngày
                                </Tag>
                              )}
                            </Space>
                          </Space>
                        </Card>
                      </List.Item>
                    );
                  }}
                />
              </div>
            );
          })
        )}
      </Spin>

      {/* Modal Đàm phán */}
      <Modal
        open={modalVisible}
        title={
          <Space direction="vertical" size={0}>
            <Space>
              <MessageOutlined />
              <span>Đàm phán: {activeNego?.player_name ?? `Player #${activeNego?.player_id}`}</span>
              <Tag color={STATUS_CONFIG[activeNego?.status]?.color}>{STATUS_CONFIG[activeNego?.status]?.label}</Tag>
            </Space>
            <Text type="secondary" style={{ fontSize: 12, marginLeft: 22 }}>
              Đối tác: {myClubId === activeNego?.buying_club_id ? `${activeNego?.selling_club_name} (Bên bán)` : `${activeNego?.buying_club_name} (Bên mua)`}
            </Text>
          </Space>
        }
        width={680}
        footer={null}
        onCancel={() => setModalVisible(false)}
      >
        {activeNego && (
          <Space direction="vertical" style={{ width: '100%' }} size={16}>
            {/* Hiệp đàm phán */}
            <Card size="small" style={{ background: '#fafafa' }}>
              <Row gutter={16}>
                <Col span={8}><Statistic title="Hiệp" value={`${activeNego.round_number}/3`} /></Col>
                <Col span={8}><Statistic title="Giá bạn bid" value={formatM(activeNego.current_offer)} valueStyle={{ color: '#1677ff' }} /></Col>
                <Col span={8}><Statistic title="Giá đối phương" value={formatM(activeNego.selling_club_demand)} valueStyle={{ color: '#cf1322' }} /></Col>
              </Row>
            </Card>

            {activeNego.status === 'INQUIRY' && (
              <>
                {myClubId === activeNego.selling_club_id ? (
                  <>
                    <Paragraph>Đối phương đã gửi Inquiry cho cầu thủ của bạn. Bạn muốn đồng ý ngồi vào bàn đàm phán không?</Paragraph>
                    <div>
                      <Text type="secondary">Đặt giá khởi điểm của bạn (€)</Text>
                      <Slider
                        min={0} max={500} step={1}
                        value={Math.round(demandValue / 1_000_000)}
                        onChange={(v) => setDemandValue(v * 1_000_000)}
                        tooltip={{ formatter: (v) => `€${v}M` }}
                      />
                      <Text strong>{formatM(demandValue)}</Text>
                    </div>
                    <Space>
                      <Button type="primary" icon={<CheckOutlined />} loading={actionLoading} onClick={() => handleRespondInquiry(true)}>Đồng ý đàm phán</Button>
                      <Button danger icon={<CloseOutlined />} loading={actionLoading} onClick={() => handleRespondInquiry(false)}>Từ chối</Button>
                    </Space>
                  </>
                ) : (
                  <>
                    <Paragraph>Bạn đang gửi Inquiry cho cầu thủ này. Chờ CLB chủ quản phản hồi...</Paragraph>
                    <Space>
                      <Button danger onClick={handleCancel}>Hủy đàm phán</Button>
                    </Space>
                  </>
                )}
              </>
            )}

            {activeNego.status === 'NEGOTIATING' && (
              <>
                {/* Hỏi đáp Q&A */}
                {/* <div>
                  <Space style={{ marginBottom: 8 }}>
                    <QuestionCircleOutlined />
                    <Text strong>Hỏi thông tin ({4 - (activeNego.questions_asked_this_round ?? 0)} câu còn lại)</Text>
                    <Button size="small" onClick={() => setQaModalVisible(true)}>Chọn câu hỏi</Button>
                  </Space>
                  {qaLog.length > 0 && (
                    <List
                      size="small"
                      bordered
                      dataSource={qaLog}
                      renderItem={(item) => (
                        <List.Item>
                          <Space direction="vertical" size={2}>
                            <Text type="secondary" style={{ fontSize: 11 }}>❓ {item.q}</Text>
                            <Text style={{ fontSize: 12 }}>💬 {item.a}</Text>
                          </Space>
                        </List.Item>
                      )}
                    />
                  )}
                </div>

                <Divider style={{ margin: '4px 0' }} /> */}

                {/* Kéo thanh giá */}
                <div style={{ marginTop: 8 }}>
                  {myClubId === activeNego.buying_club_id ? (
                    <>
                      <Text type="secondary"><DollarOutlined /> Giá bạn muốn bid (€M)</Text>
                      <Slider
                        min={0}
                        max={Math.floor((clubInfo?.budget_remaining || 500_000_000) / 1_000_000)}
                        step={0.1}
                        value={offerValue / 1_000_000}
                        onChange={(v) => setOfferValue(v * 1_000_000)}
                        tooltip={{ formatter: (v) => `€${v}M` }}
                      />
                      <Text strong style={{ color: '#1677ff' }}>{formatM(offerValue)}</Text>
                      <Button type="primary" style={{ marginLeft: 16 }} onClick={handleSubmitOffer} loading={actionLoading}>Gửi giá</Button>
                    </>
                  ) : (
                    <>
                      <Text type="secondary"><DollarOutlined /> Giá bạn muốn phản hồi (€M)</Text>
                      <Slider
                        min={0} max={500} step={0.5}
                        value={demandValue / 1_000_000}
                        onChange={(v) => setDemandValue(v * 1_000_000)}
                        tooltip={{ formatter: (v) => `€${v}M` }}
                      />
                      <Text strong style={{ color: '#cf1322' }}>{formatM(demandValue)}</Text>
                      <Button type="primary" danger style={{ marginLeft: 16 }} onClick={handleCounter} loading={actionLoading}>Phản giá</Button>
                    </>
                  )}
                </div>

                <Space style={{ marginTop: 8 }}>
                  <Button danger onClick={handleCancel}>Hủy đàm phán</Button>
                </Space>
              </>
            )}

            {(activeNego.status === 'ACCEPTED' || activeNego.status === 'CANCELLED' || activeNego.status === 'REJECTED') && (
              <Empty description={STATUS_CONFIG[activeNego.status]?.label} />
            )}
          </Space>
        )}
      </Modal>

      {/* Modal Chọn câu hỏi */}
      <Modal
        open={qaModalVisible}
        title="Chọn câu hỏi để hỏi đối phương"
        footer={null}
        onCancel={() => setQaModalVisible(false)}
        width={500}
      >
        <List
          size="small"
          dataSource={Object.entries(questions)}
          renderItem={([qId, qText]) => (
            <List.Item
              actions={[
                <Button
                  key="ask" size="small" type="link"
                  onClick={() => { handleAskQuestion(Number(qId)); setQaModalVisible(false); }}
                >Hỏi</Button>
              ]}
            >
              <Text style={{ fontSize: 12 }}>{qText as string}</Text>
            </List.Item>
          )}
        />
      </Modal>
    </div>
  );
}
