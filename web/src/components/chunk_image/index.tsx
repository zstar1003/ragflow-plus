import { Popover } from 'antd';
import classNames from 'classnames';

import styles from './index.less';

interface IImage {
  id: string;
  className: string;
}

const ChunkImage = ({ id, className, ...props }: IImage) => {
  const host = process.env.MINIO_VISIT_HOST || 'localhost';
  const port = process.env.MINIO_PORT || '9000';
  const imgSrc = `http://${host}:${port}/${id}`;
  // 检查环境变量是否被正确读取
  console.log('MinIO Config:', {
    host: process.env.MINIO_VISIT_HOST,
    port: process.env.MINIO_PORT,
  });

  return (
    <img
      {...props}
      src={imgSrc}
      alt=""
      className={classNames(styles.primitiveImg, className)}
    />
  );
};

export default ChunkImage;

export const ImageWithPopover = ({ id }: { id: string }) => {
  return (
    <Popover
      placement="left"
      content={
        <ChunkImage id={id} className={styles.imagePreview}></ChunkImage>
      }
    >
      <ChunkImage id={id} className={styles.image}></ChunkImage>
    </Popover>
  );
};
