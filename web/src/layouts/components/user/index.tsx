import { useFetchUserInfo } from '@/hooks/user-setting-hooks';
import { Avatar } from 'antd';
import React from 'react';
import { history } from 'umi';

import styles from '../../index.less';

const App: React.FC = () => {
  const { data: userInfo } = useFetchUserInfo();

  const toSetting = () => {
    history.push('/user-setting');
  };

  return (
    <Avatar
      size={32}
      onClick={toSetting}
      className={styles.clickAvailable}
      src={
        userInfo.avatar ??
        'https://picx.zhimg.com/v2-aaf12b68b54b8812e6b449e7368d30cf_l.jpg'
      }
    />
  );
};

export default App;
