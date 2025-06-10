import { Popover } from 'antd';
import classNames from 'classnames';

import api from '@/utils/api';
import { useEffect, useState } from 'react';
import styles from './index.less';

interface IImage {
  id: string;
  className: string;
}

const ChunkImage = ({ id, className, ...props }: IImage) => {
  // const host = process.env.MINIO_VISIT_HOST || 'localhost';
  // const port = process.env.MINIO_PORT || '9000';
  // const imgSrc = `http://${host}:${port}/${id}`;
  const [imgSrc, setImgSrc] = useState<string>('');

  useEffect(() => {
    const getMinioUrl = async () => {
      try {
        const res = await fetch(api.minio_endpoint);
        const data = await res.json();
        setImgSrc(`${data.url}${id}`);
      } catch (err) {
        setImgSrc(`http://localhost:9000/${id}`);
      }
    };

    getMinioUrl();
  }, [setImgSrc, id]);

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
