import MessageInput from '@/components/message-input';
import MessageItem from '@/components/message-item';
import PdfDrawer from '@/components/pdf-drawer';
import { useClickDrawer } from '@/components/pdf-drawer/hooks';
import { MessageType } from '@/constants/chat';
import {
  useFetchNextConversation,
  useGetChatSearchParams,
} from '@/hooks/chat-hooks';
import { useFetchUserInfo } from '@/hooks/user-setting-hooks';
import { buildMessageUuidWithRole } from '@/utils/chat';
import { Flex, Spin } from 'antd';
import { memo } from 'react';
import {
  useCreateConversationBeforeUploadDocument,
  useGetFileIcon,
  useGetSendButtonDisabled,
  useSendButtonDisabled,
  useSendNextMessage,
} from '../hooks';
import { buildMessageItemReference } from '../utils';
import styles from './index.less';

interface IProps {
  controller: AbortController;
  fontSize: number;
}

// 确认这里的默认值为 20
const ChatContainer = ({ controller, fontSize = 20 }: IProps) => {
  const { conversationId } = useGetChatSearchParams();
  const { data: conversation } = useFetchNextConversation();

  const {
    value,
    ref,
    loading,
    sendLoading,
    derivedMessages,
    handleInputChange,
    handlePressEnter,
    regenerateMessage,
    removeMessageById,
    stopOutputMessage,
  } = useSendNextMessage(controller);

  const { visible, hideModal, documentId, selectedChunk, clickDocumentButton } =
    useClickDrawer();
  const disabled = useGetSendButtonDisabled();
  const sendDisabled = useSendButtonDisabled(value);
  useGetFileIcon();
  const { data: userInfo } = useFetchUserInfo();
  const { createConversationBeforeUploadDocument } =
    useCreateConversationBeforeUploadDocument();

  return (
    <>
      <Flex flex={1} className={styles.chatContainer} vertical>
        <Flex
          flex={1}
          vertical
          className={styles.messageContainer}
          style={{ fontSize: `${fontSize}px` }}
        >
          <div>
            <Spin spinning={loading}>
              {derivedMessages?.map((message, i) => {
                return (
                  <MessageItem
                    loading={
                      message.role === MessageType.Assistant &&
                      sendLoading &&
                      derivedMessages.length - 1 === i
                    }
                    key={buildMessageUuidWithRole(message)}
                    item={message}
                    nickname={userInfo.nickname}
                    avatar={userInfo.avatar}
                    avatarDialog={conversation.avatar}
                    reference={buildMessageItemReference(
                      {
                        message: derivedMessages,
                        reference: conversation.reference,
                      },
                      message,
                    )}
                    clickDocumentButton={clickDocumentButton}
                    index={i}
                    removeMessageById={removeMessageById}
                    regenerateMessage={regenerateMessage}
                    sendLoading={sendLoading}
                  ></MessageItem>
                );
              })}
            </Spin>
          </div>
          <div ref={ref} />
        </Flex>
        <MessageInput
          disabled={disabled}
          sendDisabled={sendDisabled}
          sendLoading={sendLoading}
          value={value}
          onInputChange={handleInputChange}
          onPressEnter={(
            documentIds: string[],
            tempFileIds: string[] | undefined,
            tempFileInfos: any[] | undefined,
          ) => handlePressEnter(documentIds, tempFileIds, tempFileInfos)}
          conversationId={conversationId}
          useTempUpload={true}
          createConversationBeforeUploadDocument={
            createConversationBeforeUploadDocument
          }
          stopOutputMessage={stopOutputMessage}
        ></MessageInput>
      </Flex>
      <PdfDrawer
        visible={visible}
        hideModal={hideModal}
        documentId={documentId}
        chunk={selectedChunk}
      ></PdfDrawer>
    </>
  );
};

export default memo(ChatContainer);
