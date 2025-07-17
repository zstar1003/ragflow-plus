import ChunkImage from '@/components/chunk_image';
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
  Pagination,
  Space,
  Spin,
  Typography,
} from 'antd';
import { useEffect, useState } from 'react';
import { Link } from 'umi';
import { KnowledgeRouteKey } from '../../constant';
import styles from './index.less';

const { Text, Title } = Typography;

interface IKnowledgeImage {
  img_id: string;
  doc_id: string;
  doc_name: string;
  chunk_id: string;
  content: string;
}

const KnowledgeImages = () => {
  const knowledgeBaseId = useKnowledgeBaseId();
  const { t } = useTranslate('knowledgeImages');
  const [loading, setLoading] = useState(false);
  const [images, setImages] = useState<IKnowledgeImage[]>([]);
  const [searchString, setSearchString] = useState('');
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

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
      if (response.data) {
        setImages(response.data.images || []);
        setTotal(response.data.total || 0);
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
                  key={image.img_id}
                  hoverable
                  className={styles.imageCard}
                  cover={
                    <div className={styles.imageContainer}>
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
                showTotal={(total) => t('totalImages', { total })}
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
    </div>
  );
};

export default KnowledgeImages;
