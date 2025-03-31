import { Flex, Typography } from 'antd';
import classNames from 'classnames';

import { useTranslate } from '@/hooks/common-hooks';
import styles from './index.less';

const { Title } = Typography;

const LoginRightPanel = () => {
  const { t } = useTranslate('login');
  return (
    <section className={styles.rightPanel}>
      {/* <SvgIcon name="login-star" width={80}></SvgIcon> */}
      <Flex vertical gap={40}>
        <Title level={1} className={classNames(styles.pink, styles.loginTitle)}>
          {t('title')}
        </Title>
        {/* <Text className={classNames(styles.pink, styles.loginDescription)}>
          {t('description')}
        </Text>
        <Flex align="center" gap={16}>
          <Avatars></Avatars>
          <Flex vertical>
            <Space>
              <Rate disabled defaultValue={5} />
              <span
                className={classNames(styles.white, styles.loginRateNumber)}
              >
                5.0
              </span>
            </Space>
            <span className={classNames(styles.pink, styles.loginRateReviews)}>
              {t('review')}
            </span>
          </Flex>
        </Flex> */}
      </Flex>
    </section>
  );
};

export default LoginRightPanel;
