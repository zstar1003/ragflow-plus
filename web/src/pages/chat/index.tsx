import { ReactComponent as ChatAppCube } from '@/assets/svg/chat-app-cube.svg';
import EmbedModal from '@/components/api-service/embed-modal';
import { useShowEmbedModal } from '@/components/api-service/hooks';
import RenameModal from '@/components/rename-modal';
import SvgIcon from '@/components/svg-icon';
import { useTheme } from '@/components/theme-provider';
import { SharedFrom } from '@/constants/chat';
import { useSafeLocalStorageState } from '@/hooks/chat-font-hooks';
import {
  useClickConversationCard,
  useClickDialogCard,
  useFetchNextDialogList,
  useGetChatSearchParams,
} from '@/hooks/chat-hooks';
import { useTranslate } from '@/hooks/common-hooks';
import { useSetSelectedRecord } from '@/hooks/logic-hooks';
import { IDialog } from '@/interfaces/database/chat';
import { DeleteOutlined, EditOutlined } from '@ant-design/icons';
import {
  Avatar,
  Button,
  Card,
  Divider,
  Dropdown,
  Flex,
  MenuProps,
  // Modal,
  // Slider,
  Space,
  Spin,
  Tag,
  Typography,
} from 'antd';
import { MenuItemProps } from 'antd/lib/menu/MenuItem';
import classNames from 'classnames';
import { PictureInPicture2 } from 'lucide-react';
import { useCallback, useState } from 'react';
import ChatConfigurationModal from './chat-configuration-modal';
import ChatContainer from './chat-container';
import {
  useDeleteConversation,
  useDeleteDialog,
  useEditDialog,
  useHandleItemHover,
  useRenameConversation,
  useSelectDerivedConversationList,
} from './hooks';
import styles from './index.less';

const { Text } = Typography;

const FONT_SIZE_STORAGE_KEY = 'chat_font_size_v2'; // 定义一个清晰的 key (v2 用于避免旧数据干扰)
const DEFAULT_FONT_SIZE = 20; // 默认字体设为 20

const Chat = () => {
  const { data: dialogList, loading: dialogLoading } = useFetchNextDialogList();
  const { onRemoveDialog } = useDeleteDialog();
  const { onRemoveConversation } = useDeleteConversation();
  const { handleClickDialog } = useClickDialogCard();
  const { handleClickConversation } = useClickConversationCard();
  const { dialogId, conversationId } = useGetChatSearchParams();
  const { theme } = useTheme();
  const {
    list: conversationList,
    addTemporaryConversation,
    loading: conversationLoading,
  } = useSelectDerivedConversationList();
  const { activated, handleItemEnter, handleItemLeave } = useHandleItemHover();
  const {
    activated: conversationActivated,
    handleItemEnter: handleConversationItemEnter,
    handleItemLeave: handleConversationItemLeave,
  } = useHandleItemHover();
  const {
    conversationRenameLoading,
    initialConversationName,
    onConversationRenameOk,
    conversationRenameVisible,
    hideConversationRenameModal,
    showConversationRenameModal,
  } = useRenameConversation();
  const {
    dialogSettingLoading,
    initialDialog,
    onDialogEditOk,
    dialogEditVisible,
    clearDialog,
    hideDialogEditModal,
    showDialogEditModal,
  } = useEditDialog();
  const { t } = useTranslate('chat');
  const { currentRecord, setRecord } = useSetSelectedRecord<IDialog>();
  const [controller, setController] = useState(new AbortController());
  const { showEmbedModal, hideEmbedModal, embedVisible, beta } =
    useShowEmbedModal();

  const [fontSize, setFontSize] = useSafeLocalStorageState(
    FONT_SIZE_STORAGE_KEY,
    DEFAULT_FONT_SIZE,
  );
  // const [fontSizeModalVisible, setFontSizeModalVisible] = useState(false);

  const handleAppCardEnter = (id: string) => () => {
    handleItemEnter(id);
  };

  const handleConversationCardEnter = (id: string) => () => {
    handleConversationItemEnter(id);
  };

  const handleShowChatConfigurationModal =
    (dialogId?: string): any =>
    (info: any) => {
      info?.domEvent?.preventDefault();
      info?.domEvent?.stopPropagation();
      showDialogEditModal(dialogId);
    };

  const handleRemoveDialog =
    (dialogId: string): MenuItemProps['onClick'] =>
    ({ domEvent }) => {
      domEvent.preventDefault();
      domEvent.stopPropagation();
      onRemoveDialog([dialogId]);
    };

  const handleShowOverviewModal =
    (dialog: IDialog): any =>
    (info: any) => {
      info?.domEvent?.preventDefault();
      info?.domEvent?.stopPropagation();
      setRecord(dialog);
      showEmbedModal();
    };

  const handleRemoveConversation =
    (conversationId: string): MenuItemProps['onClick'] =>
    ({ domEvent }) => {
      domEvent.preventDefault();
      domEvent.stopPropagation();
      onRemoveConversation([conversationId]);
    };

  const handleShowConversationRenameModal =
    (conversationId: string): MenuItemProps['onClick'] =>
    ({ domEvent }) => {
      domEvent.preventDefault();
      domEvent.stopPropagation();
      showConversationRenameModal(conversationId);
    };

  const handleDialogCardClick = useCallback(
    (dialogId: string) => () => {
      handleClickDialog(dialogId);
    },
    [handleClickDialog],
  );

  const handleConversationCardClick = useCallback(
    (conversationId: string, isNew: boolean) => () => {
      handleClickConversation(conversationId, isNew ? 'true' : '');
      setController((pre) => {
        pre.abort();
        return new AbortController();
      });
    },
    [handleClickConversation],
  );

  const handleCreateTemporaryConversation = useCallback(() => {
    addTemporaryConversation();
  }, [addTemporaryConversation]);

  // 用于自动更新 localStorage
  // const handleFontSizeChange = (value: number) => {
  //   setFontSize(value);
  // };

  const buildAppItems = (dialog: IDialog) => {
    const dialogId = dialog.id;

    const appItems: MenuProps['items'] = [
      {
        key: '1',
        onClick: handleShowChatConfigurationModal(dialogId),
        label: (
          <Space>
            <EditOutlined />
            {t('edit', { keyPrefix: 'common' })}
          </Space>
        ),
      },
      { type: 'divider' },
      {
        key: '2',
        onClick: handleRemoveDialog(dialogId),
        label: (
          <Space>
            <DeleteOutlined />
            {t('delete', { keyPrefix: 'common' })}
          </Space>
        ),
      },
      { type: 'divider' },
      {
        key: '3',
        onClick: handleShowOverviewModal(dialog),
        label: (
          <Space>
            <PictureInPicture2 className="size-4" />
            {t('embedIntoSite', { keyPrefix: 'common' })}
          </Space>
        ),
      },
    ];

    return appItems;
  };

  const buildConversationItems = (conversationId: string) => {
    const appItems: MenuProps['items'] = [
      {
        key: '1',
        onClick: handleShowConversationRenameModal(conversationId),
        label: (
          <Space>
            <EditOutlined />
            {t('rename', { keyPrefix: 'common' })}
          </Space>
        ),
      },
      { type: 'divider' },
      {
        key: '2',
        onClick: handleRemoveConversation(conversationId),
        label: (
          <Space>
            <DeleteOutlined />
            {t('delete', { keyPrefix: 'common' })}
          </Space>
        ),
      },
    ];

    return appItems;
  };

  return (
    <Flex className={styles.chatWrapper}>
      <Flex className={styles.chatAppWrapper}>
        <Flex flex={1} vertical>
          <Button type="primary" onClick={handleShowChatConfigurationModal()}>
            {t('createAssistant')}
          </Button>
          <Divider></Divider>
          <Flex className={styles.chatAppContent} vertical gap={10}>
            <Spin spinning={dialogLoading} wrapperClassName={styles.chatSpin}>
              {dialogList.map((x) => (
                <Card
                  key={x.id}
                  hoverable
                  className={classNames(styles.chatAppCard, {
                    [theme === 'dark'
                      ? styles.chatAppCardSelectedDark
                      : styles.chatAppCardSelected]: dialogId === x.id,
                  })}
                  onMouseEnter={handleAppCardEnter(x.id)}
                  onMouseLeave={handleItemLeave}
                  onClick={handleDialogCardClick(x.id)}
                >
                  <Flex justify="space-between" align="center">
                    <Space size={15}>
                      <Avatar src={x.icon} shape={'square'} />
                      <section>
                        <b>
                          <Text
                            ellipsis={{ tooltip: x.name }}
                            style={{ width: 130 }}
                          >
                            {x.name}
                          </Text>
                        </b>
                        <div>{x.description}</div>
                      </section>
                    </Space>
                    {activated === x.id && (
                      <section>
                        <Dropdown menu={{ items: buildAppItems(x) }}>
                          <ChatAppCube
                            className={styles.cubeIcon}
                          ></ChatAppCube>
                        </Dropdown>
                      </section>
                    )}
                  </Flex>
                </Card>
              ))}
            </Spin>
          </Flex>
        </Flex>
      </Flex>
      <Divider type={'vertical'} className={styles.divider}></Divider>

      <Flex className={styles.chatTitleWrapper}>
        <Flex flex={1} vertical>
          <Flex
            justify={'space-between'}
            align="center"
            className={styles.chatTitle}
          >
            <Space>
              <b>{t('chat')}</b>
              <Tag>{conversationList.length}</Tag>
            </Space>
            <div>
              {/* <SettingOutlined
                style={{
                  marginRight: '8px',
                  fontSize: '20px',
                  cursor: 'pointer',
                }}
                onClick={() => setFontSizeModalVisible(true)}
              /> */}
              <SvgIcon
                name="plus-circle-fill"
                width={20}
                onClick={handleCreateTemporaryConversation}
              ></SvgIcon>
            </div>
          </Flex>
          <Divider></Divider>
          <Flex vertical gap={10} className={styles.chatTitleContent}>
            <Spin
              spinning={conversationLoading}
              wrapperClassName={styles.chatSpin}
            >
              {conversationList.map((x) => (
                <Card
                  key={x.id}
                  hoverable
                  onClick={handleConversationCardClick(x.id, x.is_new)}
                  onMouseEnter={handleConversationCardEnter(x.id)}
                  onMouseLeave={handleConversationItemLeave}
                  className={classNames(styles.chatTitleCard, {
                    [theme === 'dark'
                      ? styles.chatTitleCardSelectedDark
                      : styles.chatTitleCardSelected]: x.id === conversationId,
                  })}
                >
                  <Flex justify="space-between" align="center">
                    <div>
                      <Text
                        ellipsis={{ tooltip: x.name }}
                        style={{ width: 150 }}
                      >
                        {x.name}
                      </Text>
                    </div>
                    {conversationActivated === x.id &&
                      x.id !== '' &&
                      !x.is_new && (
                        <section>
                          <Dropdown
                            menu={{ items: buildConversationItems(x.id) }}
                          >
                            <ChatAppCube
                              className={styles.cubeIcon}
                            ></ChatAppCube>
                          </Dropdown>
                        </section>
                      )}
                  </Flex>
                </Card>
              ))}
            </Spin>
          </Flex>
        </Flex>
      </Flex>
      <Divider type={'vertical'} className={styles.divider}></Divider>
      <ChatContainer
        controller={controller}
        fontSize={fontSize}
      ></ChatContainer>
      {dialogEditVisible && (
        <ChatConfigurationModal
          visible={dialogEditVisible}
          initialDialog={initialDialog}
          showModal={showDialogEditModal}
          hideModal={hideDialogEditModal}
          loading={dialogSettingLoading}
          onOk={onDialogEditOk}
          clearDialog={clearDialog}
        ></ChatConfigurationModal>
      )}
      <RenameModal
        visible={conversationRenameVisible}
        hideModal={hideConversationRenameModal}
        onOk={onConversationRenameOk}
        initialName={initialConversationName}
        loading={conversationRenameLoading}
      ></RenameModal>

      {embedVisible && (
        <EmbedModal
          visible={embedVisible}
          hideModal={hideEmbedModal}
          token={currentRecord.id}
          form={SharedFrom.Chat}
          beta={beta}
          isAgent={false}
        ></EmbedModal>
      )}

      {/* {fontSizeModalVisible && (
        <Modal
          title={'设置字体大小'}
          open={fontSizeModalVisible}
          onCancel={() => setFontSizeModalVisible(false)}
          footer={null}
        >
          <Flex vertical gap="middle" align="center">
            {'当前字体大小'}: {fontSize}px
            <Slider
              min={16}
              max={24}
              step={1}
              value={fontSize}
              style={{ width: '80%' }}
              onChange={handleFontSizeChange}
            />
          </Flex>
        </Modal>
      )} */}
    </Flex>
  );
};

export default Chat;
