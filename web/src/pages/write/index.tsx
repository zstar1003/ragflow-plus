import HightLightMarkdown from '@/components/highlight-markdown';
import { useTranslate } from '@/hooks/common-hooks';
import { aiAssistantConfig } from '@/pages/write/ai-assistant-config';
import {
  Button,
  Card,
  Flex,
  Input,
  Layout,
  List,
  Space,
  Tabs,
  message,
} from 'antd';
import axios from 'axios';
import { Document, Packer, Paragraph, TextRun } from 'docx';
import { saveAs } from 'file-saver';
import { marked } from 'marked';
import { useEffect, useRef, useState } from 'react';

const { Sider, Content } = Layout;
const { TabPane } = Tabs;

interface TemplateItem {
  id: string;
  name: string;
  content: string;
}

const Write = () => {
  const { t } = useTranslate('write');
  const [content, setContent] = useState('');
  const [aiQuestion, setAiQuestion] = useState('');
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [dialogId, setDialogId] = useState('');
  const [cursorPosition, setCursorPosition] = useState<number | null>(null);
  const [showCursorIndicator, setShowCursorIndicator] = useState(false);
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  // 定义模板内容
  const [templates] = useState<TemplateItem[]>([
    {
      id: '1',
      name: t('defaultTemplate'),
      content: `# ${t('defaultTemplateTitle')}

  ## ${t('introduction')}


  ## ${t('mainContent')}
  
  ## ${t('conclusion')}
  `,
    },
    {
      id: '2',
      name: t('technicalDoc'),
      content: `# ${t('technicalDocTitle')}
  
  ## ${t('overview')}
  
  ## ${t('requirements')}
  
  ## ${t('architecture')}
  
  ## ${t('implementation')}
  
  ## ${t('testing')}
  
  ## ${t('deployment')}
  
  ## ${t('maintenance')}
  `,
    },
    {
      id: '3',
      name: t('meetingMinutes'),
      content: `# ${t('meetingMinutesTitle')}
  
  ## ${t('date')}: ${new Date().toLocaleDateString()}
  
  ## ${t('participants')}
  
  ## ${t('agenda')}
  
  ## ${t('discussions')}
  
  ## ${t('decisions')}
  
  ## ${t('actionItems')}
  
  ## ${t('nextMeeting')}
  `,
    },
  ]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('1');
  const [viewMode, setViewMode] = useState<'edit' | 'preview' | 'split'>(
    'split',
  );

  // 在组件加载时获取对话列表
  useEffect(() => {
    const fetchDialogList = async () => {
      try {
        const authorization = localStorage.getItem('Authorization');
        if (!authorization) return;

        const response = await axios.get('/v1/dialog/list', {
          headers: {
            authorization: authorization,
          },
        });

        if (response.data?.data?.length > 0) {
          // 使用第一个对话的ID
          setDialogId(response.data.data[0].id);
        }
      } catch (error) {
        console.error('获取对话列表失败:', error);
      }
    };

    fetchDialogList();
  }, []);

  // 处理模板选择
  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplate(templateId);
    // 查找选中的模板
    const selectedTemplateItem = templates.find(
      (item) => item.id === templateId,
    );
    if (selectedTemplateItem) {
      // 填充模板内容
      setContent(selectedTemplateItem.content);
    }
  };

  // 实现保存为Word功能
  const handleSave = () => {
    // 获取当前选中的模板名称
    const selectedTemplateItem = templates.find(
      (item) => item.id === selectedTemplate,
    );
    if (!selectedTemplateItem) return;

    // 生成文件名：模板名+当前日期，例如：学术论文20250319.docx
    const today = new Date();
    const dateStr = `${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, '0')}${String(today.getDate()).padStart(2, '0')}`;
    const fileName = `${selectedTemplateItem.name}${dateStr}.docx`;

    // 使用 marked 解析 Markdown 内容
    const tokens = marked.lexer(content);

    // 创建段落数组
    const paragraphs: Paragraph[] = [];

    tokens.forEach((token) => {
      if (token.type === 'heading') {
        // 处理标题
        const headingToken = token as any; // 使用 any 类型绕过 marked.Tokens 问题
        let headingType:
          | 'Heading1'
          | 'Heading2'
          | 'Heading3'
          | 'Heading4'
          | 'Heading5'
          | 'Heading6'
          | undefined;

        // 根据标题级别设置正确的标题类型
        switch (headingToken.depth) {
          case 1:
            headingType = 'Heading1';
            break;
          case 2:
            headingType = 'Heading2';
            break;
          case 3:
            headingType = 'Heading3';
            break;
          case 4:
            headingType = 'Heading4';
            break;
          case 5:
            headingType = 'Heading5';
            break;
          case 6:
            headingType = 'Heading6';
            break;
          default:
            headingType = 'Heading1';
        }

        paragraphs.push(
          new Paragraph({
            children: [
              new TextRun({
                text: headingToken.text,
                size: 28 - headingToken.depth * 2,
              }),
            ],
            heading: headingType,
            spacing: { after: 200 - headingToken.depth * 40 },
          }),
        );
      } else if (token.type === 'paragraph') {
        // 处理段落
        const paraToken = token as any; // 使用 any 类型绕过 marked.Tokens 问题
        paragraphs.push(
          new Paragraph({
            children: [
              new TextRun({
                text: paraToken.text,
              }),
            ],
            spacing: { after: 80 },
          }),
        );
      } else if (token.type === 'space') {
        // 处理空行
        paragraphs.push(new Paragraph({}));
      }
      // 可以根据需要添加对其他类型的处理，如列表、表格等
    });

    // 将所有段落添加到文档中
    const doc = new Document({
      sections: [
        {
          children: paragraphs,
        },
      ],
    });

    // 生成并下载 Word 文档
    Packer.toBlob(doc).then((blob) => {
      saveAs(blob, fileName);
    });
  };
  // 渲染编辑器部分
  const renderEditor = () => (
    <div style={{ position: 'relative', height: '100%' }}>
      <Input.TextArea
        ref={textAreaRef}
        style={{
          height: '100%',
          border: 'none',
          padding: 24,
          fontSize: 16,
          resize: 'none',
        }}
        value={content}
        onChange={(e) => setContent(e.target.value)}
        onClick={(e) => {
          // 记录点击位置的光标位置
          const target = e.target as HTMLTextAreaElement;
          setCursorPosition(target.selectionStart);
          setShowCursorIndicator(true); // 显示光标指示器
        }}
        onKeyUp={(e) => {
          // 更新键盘操作后的光标位置
          const target = e.target as HTMLTextAreaElement;
          setCursorPosition(target.selectionStart);
          setShowCursorIndicator(true); // 显示光标指示器
        }}
        placeholder={t('writePlaceholder')}
        autoSize={false}
      />
      {showCursorIndicator && cursorPosition !== null && (
        <div
          style={{
            position: 'absolute',
            top: 8,
            right: 8,
            background: '#1890ff',
            color: 'white',
            padding: '2px 8px',
            borderRadius: 4,
            fontSize: 12,
            opacity: 0.8,
            zIndex: 10,
          }}
        >
          已锁定插入位置
        </div>
      )}
    </div>
  );

  // 渲染预览部分
  const renderPreview = () => (
    <div
      style={{
        height: '100%',
        padding: 24,
        overflow: 'auto',
        fontSize: 16,
      }}
    >
      <HightLightMarkdown>
        {content || t('previewPlaceholder')}
      </HightLightMarkdown>
    </div>
  );

  // 根据视图模式渲染内容
  const renderContent = () => {
    switch (viewMode) {
      case 'edit':
        return renderEditor();
      case 'preview':
        return renderPreview();
      case 'split':
      default:
        return (
          <Flex style={{ height: '100%' }}>
            <div
              style={{
                width: '50%',
                borderRight: '1px solid #f0f0f0',
                height: '100%',
              }}
            >
              {renderEditor()}
            </div>
            <div style={{ width: '50%', height: '100%' }}>
              {renderPreview()}
            </div>
          </Flex>
        );
    }
  };

  // 处理 AI 助手问题提交
  const handleAiQuestionSubmit = async (
    e: React.KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();

      if (!aiQuestion.trim()) {
        message.warning('请输入问题');
        return;
      }

      if (!dialogId) {
        message.error('未找到可用的对话');
        return;
      }

      setIsAiLoading(true);

      // 保存初始光标位置和内容，用于动态更新
      const initialCursorPos = cursorPosition;
      const initialContent = content;
      let beforeCursor = '';
      let afterCursor = '';

      // 确定插入位置
      if (initialCursorPos !== null && showCursorIndicator) {
        beforeCursor = initialContent.substring(0, initialCursorPos);
        afterCursor = initialContent.substring(initialCursorPos);
      }

      // 创建一个可以取消的请求控制器
      const controller = new AbortController();
      // 设置超时定时器
      const timeoutId = setTimeout(() => {
        controller.abort();
      }, aiAssistantConfig.api.timeout || 30000);

      try {
        const authorization = localStorage.getItem('Authorization');
        if (!authorization) {
          message.error('未登录，请先登录');
          setIsAiLoading(false);
          return;
        }

        // 生成一个随机的会话ID
        const conversationId =
          Math.random().toString(36).substring(2) + Date.now().toString(36);

        // 创建新会话
        try {
          const createSessionResponse = await axios.post(
            'v1/conversation/set',
            {
              dialog_id: dialogId,
              name: '文档撰写对话',
              is_new: true,
              conversation_id: conversationId,
              message: [
                {
                  role: 'assistant',
                  content: '新对话',
                },
              ],
            },
            {
              headers: {
                authorization: authorization,
              },
              signal: controller.signal,
            },
          );

          if (!createSessionResponse.data?.data?.id) {
            message.error('创建会话失败');
            setIsAiLoading(false);
            return;
          }
        } catch (error) {
          console.error('创建会话失败:', error);
          message.error('创建会话失败，请重试');
          setIsAiLoading(false);
          return;
        }

        // 组合当前问题和编辑器内容
        const combinedQuestion = `${aiQuestion}\n\n当前文档内容：\n${content}`;

        console.log('发送问题到 AI 助手:', aiQuestion);

        let lastContent = ''; // 上一次的累积内容

        try {
          const response = await axios.post(
            '/v1/conversation/completion',
            {
              conversation_id: conversationId,
              messages: [
                {
                  role: 'user',
                  content: combinedQuestion,
                },
              ],
            },
            {
              timeout: aiAssistantConfig.api.timeout,
              headers: {
                authorization: authorization,
              },
              signal: controller.signal,
            },
          );

          // 修改响应处理逻辑，实现在光标位置动态插入内容
          if (response.data) {
            const lines = response.data
              .split('\n')
              .filter((line: string) => line.trim());

            // 直接处理每一行数据，不使用嵌套的 Promise
            for (let i = 0; i < lines.length; i++) {
              try {
                const jsonStr = lines[i].replace('data:', '').trim();
                const jsonData = JSON.parse(jsonStr);

                if (jsonData.code === 0 && jsonData.data?.answer) {
                  const answer = jsonData.data.answer;

                  // 过滤掉 think 标签内容
                  const cleanedAnswer = answer
                    .replace(/<think>[\s\S]*?<\/think>/g, '')
                    .trim();
                  // 检查是否还有未闭合的 think 标签
                  const hasUnclosedThink =
                    cleanedAnswer.includes('<think>') &&
                    (!cleanedAnswer.includes('</think>') ||
                      cleanedAnswer.indexOf('<think>') >
                        cleanedAnswer.lastIndexOf('</think>'));

                  if (cleanedAnswer && !hasUnclosedThink) {
                    // 计算新增的内容部分
                    const newContent = cleanedAnswer;
                    const incrementalContent = newContent.substring(
                      lastContent.length,
                    );

                    // 只有当有新增内容时才更新编辑器
                    if (incrementalContent) {
                      // 更新上一次的内容记录
                      lastContent = newContent;

                      // 动态更新编辑器内容
                      if (initialCursorPos !== null && showCursorIndicator) {
                        // 在光标位置动态插入内容
                        setContent(beforeCursor + newContent + afterCursor);

                        // 更新光标位置到插入内容之后
                        const newPosition =
                          initialCursorPos + newContent.length;
                        setCursorPosition(newPosition);
                      } else {
                        // 如果没有光标位置，则追加到末尾
                        setContent(initialContent + newContent);
                      }
                    }
                  }
                }
              } catch (parseErr) {
                console.error('解析单行数据失败:', parseErr);
                // 继续处理下一行，不中断整个流程
              }

              // 添加一个小延迟，让UI有时间更新
              if (i < lines.length - 1) {
                await new Promise((resolve) => setTimeout(resolve, 10));
              }
            }
          }
        } catch (error: any) {
          console.error('获取 AI 回答失败:', error);
          // 检查是否是超时错误
          if (error.code === 'ECONNABORTED' || error.name === 'AbortError') {
            message.error('AI 助手响应超时，请稍后重试');
          } else {
            message.error('获取 AI 回答失败，请重试');
          }
        } finally {
          // 清除超时定时器
          clearTimeout(timeoutId);
        }

        // 在处理完所有响应后，删除临时会话
        try {
          await axios.post(
            '/v1/conversation/rm',
            {
              conversation_ids: [conversationId],
              dialog_id: dialogId,
            },
            {
              headers: {
                authorization: authorization,
              },
            },
          );
          console.log('临时会话已删除:', conversationId);

          // 处理完成后，重新设置光标焦点
          if (textAreaRef.current) {
            textAreaRef.current.focus();
          }
        } catch (rmErr) {
          console.error('删除临时会话失败:', rmErr);
          // 删除会话失败不影响主流程
        }
      } catch (err) {
        console.error('AI 助手处理失败:', err);
        message.error('AI 助手处理失败，请重试');
      } finally {
        setIsAiLoading(false);
        // 清空问题输入框
        setAiQuestion('');
      }
    }
  };
  return (
    <Layout style={{ height: 'auto', padding: 24, overflow: 'hidden' }}>
      <Sider
        width={280}
        theme="light"
        style={{
          borderRight: '1px solid #f0f0f0',
          padding: '0 16px',
          overflow: 'auto',
          height: '100%',
        }}
      >
        <List
          header={
            <div className="templateHeader" style={{ textAlign: 'center' }}>
              {t('templateList')}
            </div>
          }
          dataSource={templates}
          renderItem={(item) => (
            <List.Item
              actions={[
                <a
                  key="select"
                  onClick={() => handleTemplateSelect(item.id)}
                ></a>,
              ]}
              style={{
                cursor: 'pointer',
                background: selectedTemplate === item.id ? '#f0f7ff' : 'none',
                borderRadius: 8,
                paddingLeft: 12,
              }}
              onClick={() => handleTemplateSelect(item.id)}
            >
              <span className="templateItemText">{item.name}</span>
            </List.Item>
          )}
        />
      </Sider>
      <Content style={{ paddingLeft: 24 }}>
        <Flex vertical style={{ height: '100%', gap: 16 }}>
          <Flex
            justify="space-between"
            align="center"
            style={{ marginBottom: 16 }}
          >
            <h2 className="pageTitle">{t('writeDocument')}</h2>
            <Space>
              <Button.Group>
                <Button
                  type={viewMode === 'edit' ? 'primary' : 'default'}
                  onClick={() => setViewMode('edit')}
                >
                  {t('edit')}
                </Button>
                <Button
                  type={viewMode === 'split' ? 'primary' : 'default'}
                  onClick={() => setViewMode('split')}
                >
                  {t('split')}
                </Button>
                <Button
                  type={viewMode === 'preview' ? 'primary' : 'default'}
                  onClick={() => setViewMode('preview')}
                >
                  {t('preview')}
                </Button>
              </Button.Group>
              <Button type="primary" onClick={handleSave}>
                {t('save')}
              </Button>
            </Space>
          </Flex>
          <Card
            bodyStyle={{
              padding: 0,
              height: 'calc(70vh - 100px)',
              overflow: 'hidden',
              position: 'relative',
            }}
          >
            {renderContent()}
          </Card>
          <Card
            title={t('aiAssistant')}
            bodyStyle={{
              padding: 10,
              height: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
            }}
          >
            <div className="dialogContainer">
              {isAiLoading && (
                <div style={{ textAlign: 'center' }}>
                  <div>AI 助手正在思考中...</div>
                </div>
              )}
              <Input.TextArea
                className="inputArea"
                placeholder={t('askAI')}
                autoSize={{ minRows: 3, maxRows: 6 }}
                value={aiQuestion}
                onChange={(e) => setAiQuestion(e.target.value)}
                onKeyDown={handleAiQuestionSubmit}
                disabled={isAiLoading}
              />
            </div>
          </Card>
        </Flex>
      </Content>
    </Layout>
  );
};

export default Write;
