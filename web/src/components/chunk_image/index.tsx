import { Popover } from 'antd';
import classNames from 'classnames';

import styles from './index.less';

interface IImage {
  id: string;
  className: string;
}

const ChunkImage = ({ id, className, ...props }: IImage) => {
  const imgSrc = id;

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
