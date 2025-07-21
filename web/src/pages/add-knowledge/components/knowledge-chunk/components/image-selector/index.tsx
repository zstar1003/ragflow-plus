import { useTranslate } from '@/hooks/common-hooks';
import { useKnowledgeBaseId } from '@/hooks/knowledge-hooks';
import api from '@/utils/api';
import request from '@/utils/request';
import { SearchOutlined } from '@ant-design/icons';
import {
  Card,
  Empty,
  Flex,
  Input,
  Modal,
  Pagination,
  Spin,
  Typography,
  message,
} from 'antd';
import { useEffect, useState } from 'react';
import ChunkImage from '@/components/chunk_image';
import styles from './index.less';

const { Text } = Typography;

interface IKnowledgeImage {
  img_id: string;
  doc_id: string;
  doc_name: string;
  chunk_id: string;
  content: string;
}

interface ImageSelectorProps {
  visible: boolean;
  onCancel: () => void;
  onSelect: (imageId: string) => void;
  selectedImageId?: string;
}

const ImageSelector = ({ visible, onCancel, onSelect, selectedImageId }: ImageSelectorProps) => {
  const knowledgeBaseId = useKnowledgeBaseId();
  const { t } = useTranslate('knowledgeImages');
  const [loading, setLoading] = useState(false);
  const [images, setImages] = useState<IKnowledgeImage[]>([]);
  const [searchString, setSearchString] = useState('');
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 12; // 每页显示12张图片

  const fetchImages = async (page = 1, size = 12, search = '') => {
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
      const responseData = response.data;
      if (responseData && responseData.code === 0 && responseData.data) {
        setImages(responseData.data.images || []);
        setTotal(responseData.data.total || 0);
      }
    } catch (error) {
      console.error('Failed to fetch knowledge images:', error);
      message.error('获取图片列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (visible && knowledgeBaseId) {
      fetchImages(currentPage, pageSize, searchString);
    }
  }, [visible, knowledgeBaseId, currentPage, pageSize, searchString]);

  const handleSearch = (value: string) => {
    setSearchString(value);
    setCurrentPage(1);
    fetchImages(1, pageSize, value);
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    fetchImages(page, pageSize, searchString);
  };

  const handleImageSelect = (imageId: string) => {
    onSelect(imageId);
    onCancel();
  };

  const handleRemoveImage = () => {
    onSelect(''); // 传递空字符串表示移除图片
    onCancel();
  };

  return (
    <Modal
      title="选择关联图片"
      open={visible}
      onCancel={onCancel}
      width={800}
      footer={[
        <div key="footer" style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
          <div>
            {selectedImageId && (
              <button
                type="button"
                onClick={handleRemoveImage}
                style={{
                  background: 'none',
                  border: '1px solid #ff4d4f',
                  color: '#ff4d4f',
                  padding: '4px 15px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                }}
              >
                移除关联图片
              </button>
            )}
          </div>
          <button
            type="button"
            onClick={onCancel}
            style={{
              background: 'none',
              border: '1px solid #d9d9d9',
              color: '#000',
              padding: '4px 15px',
              borderRadius: '6px',
              cursor: 'pointer',
            }}
          >
            取消
          </button>
        </div>
      ]}
    >
      <div style={{ marginBottom: 16 }}>
        <Input
          placeholder="搜索图片..."
          prefix={<SearchOutlined />}
          value={searchString}
          onChange={(e) => handleSearch(e.target.value)}
          allowClear
        />
      </div>

      <Spin spinning={loading}>
        {images.length > 0 ? (
          <>
            <div className={styles.imagesGrid}>
              {images.map((image) => (
                <Card
                  key={image.chunk_id}
                  hoverable
                  className={`${styles.imageCard} ${selectedImageId === image.img_id ? styles.selected : ''}`}
                  cover={
                    <div className={styles.imageContainer}>
                      <ChunkImage
                        id={image.img_id}
                        className={styles.image}
                      />
                    </div>
                  }
                  onClick={() => handleImageSelect(image.img_id)}
                >
                  <Card.Meta
                    title={
                      <Text ellipsis={{ tooltip: image.doc_name }}>
                        {image.doc_name}
                      </Text>
                    }
                    description={
                      <Text ellipsis={{ tooltip: image.content }}>
                        {image.content}
                      </Text>
                    }
                  />
                </Card>
              ))}
            </div>

            {total > pageSize && (
              <div style={{ textAlign: 'center', marginTop: 16 }}>
                <Pagination
                  current={currentPage}
                  total={total}
                  pageSize={pageSize}
                  onChange={handlePageChange}
                  showSizeChanger={false}
                  showQuickJumper
                  showTotal={(total, range) =>
                    `${range[0]}-${range[1]} 共 ${total} 张图片`
                  }
                />
              </div>
            )}
          </>
        ) : (
          <Empty description="暂无图片" />
        )}
      </Spin>
    </Modal>
  );
};

export default ImageSelector;
