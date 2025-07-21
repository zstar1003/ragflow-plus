/* eslint-disable react-hooks/exhaustive-deps */
import { useTranslate } from '@/hooks/common-hooks';
import { useKnowledgeBaseId } from '@/hooks/knowledge-hooks';
import api from '@/utils/api';
import request from '@/utils/request';
import { ArrowLeftOutlined, SearchOutlined } from '@ant-design/icons';
import {
  Breadcrumb,
  Card,
  Divider,
  Empty,
  Flex,
  Input,
  Modal,
  Pagination,
  Space,
  Spin,
  Typography,
} from 'antd';
import { useEffect, useState } from 'react';
import { Link } from 'umi';
import { KnowledgeRouteKey } from '../../constant';
import styles from './index.less';

const { Text } = Typography;

interface IKnowledgeImage {
  img_id: string;
  doc_id: string;
  doc_name: string;
  chunk_id: string;
  content: string;
}

// 图片组件
const ChunkImage = ({
  id,
  className,
  imageInfo,
  onPreview,
  ...props
}: {
  id: string;
  className: string;

  imageInfo?: IKnowledgeImage;
  onPreview?: () => void;
}) => {
  const [imgSrc, setImgSrc] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const tryLoadImage = async () => {
      setLoading(true);
      setError('');

      try {
        const res = await fetch(api.minio_endpoint);
        const data = await res.json();
        const directUrl = `${data.url}${id}`;
        setImgSrc(directUrl);
        setLoading(false);
        return;
      } catch (err) {
        setError('Failed to load image');
        setLoading(false);
      }
    };

    tryLoadImage();
  }, [id]);

  // 清理blob URL，避免内存泄漏
  useEffect(() => {
    return () => {
      if (imgSrc && imgSrc.startsWith('blob:')) {
        URL.revokeObjectURL(imgSrc);
      }
    };
  }, [imgSrc]);

  if (loading) {
    return (
      <div
        style={{
          width: '100px',
          height: '100px',
          background: '#f0f0f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '10px',
        }}
      >
        Loading...
      </div>
    );
  }

  if (error && !imgSrc) {
    return (
      <div
        style={{
          width: '100px',
          height: '100px',
          background: '#ffebee',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '10px',
          textAlign: 'center',
        }}
      >
        Load Failed
      </div>
    );
  }

  return (
    <div
      style={{ position: 'relative', cursor: 'pointer' }}
      onClick={onPreview}
      title="点击预览"
    >
      <img
        {...props}
        src={imgSrc}
        alt={imageInfo?.doc_name || ''}
        className={className}
        onError={() => setError('Image load failed')}
      />
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          opacity: 0,
          transition: 'opacity 0.3s',
          color: 'white',
          fontSize: '12px',
        }}
        className="image-overlay"
      >
        🔍 点击预览
      </div>
    </div>
  );
};

const KnowledgeImages = () => {
  const knowledgeBaseId = useKnowledgeBaseId();
  const { t } = useTranslate('knowledgeImages');
  const [loading, setLoading] = useState(false);
  const [images, setImages] = useState<IKnowledgeImage[]>([]);
  const [searchString, setSearchString] = useState('');
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewImage, setPreviewImage] = useState<IKnowledgeImage | null>(
    null,
  );

  const fetchImages = async (page = 1, size = 20, search = '') => {
    setLoading(true);
    try {
      const response = await request.get(api.kb_images, {
        params: {
          kb_id: knowledgeBaseId,
          page,
          page_size: size,
          search,
        },
      });
      // 获取响应数据
      const responseData = response.data;
      if (responseData && responseData.code === 0 && responseData.data) {
        setImages(responseData.data.images || []);
        setTotal(responseData.data.total || 0);
      }
    } catch (error) {
      console.error('Failed to fetch knowledge images:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (knowledgeBaseId) {
      fetchImages(currentPage, pageSize, searchString);
    }
  }, [knowledgeBaseId, currentPage, pageSize]);

  const handleSearch = (value: string) => {
    setSearchString(value);
    setCurrentPage(1);
    fetchImages(1, pageSize, value);
  };

  const handlePageChange = (page: number, size?: number) => {
    setCurrentPage(page);
    if (size && size !== pageSize) {
      setPageSize(size);
    }
    fetchImages(page, size || pageSize, searchString);
  };

  const handlePreview = (image: IKnowledgeImage) => {
    setPreviewImage(image);
    setPreviewVisible(true);
  };

  const handleClosePreview = () => {
    setPreviewVisible(false);
    setPreviewImage(null);
  };

  return (
    <div className={styles.imagesPage}>
      <Flex justify="space-between" align="center" className={styles.header}>
        <Space size="middle">
          <Link
            to={`/knowledge/${KnowledgeRouteKey.Dataset}?id=${knowledgeBaseId}`}
          >
            <ArrowLeftOutlined />
          </Link>
          <Breadcrumb
            items={[
              {
                title: (
                  <Link
                    to={`/knowledge/${KnowledgeRouteKey.Dataset}?id=${knowledgeBaseId}`}
                  >
                    {t('dataset')}
                  </Link>
                ),
              },
              {
                title: t('images'),
              },
            ]}
          />
        </Space>
        <Input
          placeholder={t('searchPlaceholder')}
          prefix={<SearchOutlined />}
          value={searchString}
          onChange={(e) => handleSearch(e.target.value)}
          style={{ width: 250 }}
          allowClear
        />
      </Flex>
      <Divider />

      <Spin spinning={loading}>
        {images.length > 0 ? (
          <>
            <Flex wrap="wrap" gap="middle" className={styles.imagesGrid}>
              {images.map((image) => (
                <Card
                  key={image.chunk_id}
                  hoverable
                  className={styles.imageCard}
                  cover={
                    <div className={styles.imageContainer}>
                      <ChunkImage
                        id={image.img_id}
                        className={styles.image}
                        imageInfo={image}
                        onPreview={() => handlePreview(image)}
                      />
                      <ChunkImage id={image.img_id} className={styles.image} />
                    </div>
                  }
                >
                  <Card.Meta
                    title={
                      <Link
                        to={`/knowledge/${KnowledgeRouteKey.Dataset}/chunk?id=${knowledgeBaseId}&doc_id=${image.doc_id}`}
                      >
                        {image.doc_name}
                      </Link>
                    }
                    description={
                      <Text ellipsis={{ tooltip: image.content }}>
                        {image.content}
                      </Text>
                    }
                  />
                </Card>
              ))}
            </Flex>
            <Flex justify="center" className={styles.pagination}>
              <Pagination
                current={currentPage}
                pageSize={pageSize}
                total={total}
                onChange={handlePageChange}
                showSizeChanger
                showTotal={(totalCount) => `共 ${totalCount} 张图片`}
              />
            </Flex>
          </>
        ) : (
          <Empty
            description={t('noImages')}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        )}
      </Spin>
      {/* 图片预览Modal */}
      <Modal
        open={previewVisible}
        onCancel={handleClosePreview}
        footer={null}
        width="90vw"
        style={{ top: 20 }}
        centered
      >
        {previewImage && (
          <div style={{ textAlign: 'center' }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                minHeight: '50vh',
                marginBottom: '16px',
              }}
            >
              <img
                src={`http://localhost:9000/${previewImage.img_id}`}
                alt={previewImage.doc_name}
                style={{
                  maxWidth: '100%',
                  maxHeight: '70vh',
                  objectFit: 'contain',
                  display: 'block',
                }}
              />
            </div>
            <div
              style={{
                marginTop: '16px',
                padding: '16px',
                background: '#f5f5f5',
                borderRadius: '8px',
                textAlign: 'left',
              }}
            >
              <div
                style={{
                  marginBottom: '8px',
                  fontSize: '16px',
                  fontWeight: 'bold',
                }}
              >
                📄 {previewImage.doc_name}
              </div>
              <div style={{ fontSize: '14px', lineHeight: '1.5' }}>
                {previewImage.content}
              </div>
              <div
                style={{ marginTop: '8px', fontSize: '12px', color: '#666' }}
              >
                图片ID: {previewImage.img_id.split('/').pop()}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default KnowledgeImages;
