import SvgIcon from '@/components/svg-icon';
import { useFetchSystemStatus } from '@/hooks/user-setting-hooks';
import { ISystemStatus } from '@/interfaces/database/user-setting';
import { toFixed } from '@/utils/common-util';
import { Badge, Card, Flex, Spin, Typography } from 'antd';
import classNames from 'classnames';
import lowerCase from 'lodash/lowerCase';
import upperFirst from 'lodash/upperFirst';
import { useEffect } from 'react';
import styles from './index.less';

const { Text } = Typography;

enum Status {
  'green' = 'success',
  'red' = 'error',
  'yellow' = 'warning',
}

const TitleMap = {
  doc_engine: 'Doc Engine',
  storage: 'Object Storage',
  redis: 'Redis',
  database: 'Database',
};

const IconMap = {
  doc_engine: 'storage',
  redis: 'redis',
  storage: 'minio',
  database: 'database',
};

const SystemInfo = () => {
  const {
    systemStatus,
    fetchSystemStatus,
    loading: statusLoading,
  } = useFetchSystemStatus();

  useEffect(() => {
    fetchSystemStatus();
  }, [fetchSystemStatus]);

  return (
    <section className={styles.systemInfo}>
      <Spin spinning={statusLoading}>
        <Flex gap={16} vertical>
          {Object.keys(systemStatus).map((key) => {
            const info = systemStatus[key as keyof ISystemStatus];
            return (
              <Card
                type="inner"
                title={
                  <Flex align="center" gap={10}>
                    {key === 'task_executor_heartbeats' ? (
                      <div></div>
                    ) : (
                      // <img src="/logo.svg" alt="" width={26} />
                      // 各组件Icon
                      <SvgIcon
                        name={IconMap[key as keyof typeof IconMap]}
                        width={26}
                      ></SvgIcon>
                    )}
                    <span className={styles.title}>
                      {TitleMap[key as keyof typeof TitleMap]}
                    </span>
                    <Badge
                      className={styles.badge}
                      status={Status[info.status as keyof typeof Status]}
                    />
                  </Flex>
                }
                key={key}
              >
                {key === 'task_executor_heartbeats' ? (
                  <div> </div>
                ) : (
                  Object.keys(info)
                    .filter((x) => x !== 'status')
                    .map((x) => {
                      return (
                        <Flex
                          key={x}
                          align="center"
                          gap={16}
                          className={styles.text}
                        >
                          <b>{upperFirst(lowerCase(x))}:</b>
                          {/* 卡片具体文字数值 */}
                          <Text
                            className={classNames({
                              [styles.error]: x === 'error',
                            })}
                          >
                            {toFixed((info as Record<string, any>)[x]) as any}
                            {x === 'elapsed' && ' ms'}
                          </Text>
                        </Flex>
                      );
                    })
                )}
              </Card>
            );
          })}
        </Flex>
      </Spin>
    </section>
  );
};

export default SystemInfo;
