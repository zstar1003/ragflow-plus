import { api_host } from '@/utils/api';
import { Popover } from 'antd';
import classNames from 'classnames';

import styles from './index.less';

interface IImage {
  id: string;
  className: string;
}

const ChunkImage = ({ id, className, ...props }: IImage) => {
  return (
    <img
      {...props}
      src={`${api_host}/document/image/${id}`}
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
