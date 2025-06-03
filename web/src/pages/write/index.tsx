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
  message,
  Modal,
  Popconfirm,
  Space,
  Typography,
} from 'antd';
import axios from 'axios';
import { Document, Packer, Paragraph, TextRun } from 'docx';
import { saveAs } from 'file-saver';
import { marked } from 'marked';
import { useEffect, useRef, useState } from 'react';

const { Sider, Content } = Layout;

const LOCAL_STORAGE_TEMPLATES_KEY = 'userWriteTemplates'; // localStorage的键名

interface TemplateItem {
  id: string;
  name: string;
  content: string;
  isCustom?: boolean; // true 表示用户自定义的，false 或 undefined 表示初始默认的
  // isDefault?: boolean; // 可以用这个来明确标记是否是最初的默认模板，可选
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

  // 模板状态，将从localStorage加载
  const [templates, setTemplates] = useState<TemplateItem[]>([]);

  const [isTemplateModalVisible, setIsTemplateModalVisible] = useState(false);
  const [templateName, setTemplateName] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<string>(''); // 初始不选定或选定第一个
  const [viewMode, setViewMode] = useState<'edit' | 'preview' | 'split'>(
    'split',
  );

  // 获取初始默认模板的函数，方便复用
  const getInitialDefaultTemplates = (): TemplateItem[] => [
    {
      id: 'default_1', // 修改ID，避免与用户自定义的纯数字ID潜在冲突
      name: t('defaultTemplate'),
      content: `# ${t('defaultTemplateTitle')}\n\n  ## ${t('introduction')}\n\n\n  ## ${t('mainContent')}\n  \n  ## ${t('conclusion')}\n  `,
      isCustom: false,
    },
    {
      id: 'default_2',
      name: t('technicalDoc'),
      content: `# ${t('technicalDocTitle')}\n  \n  ## ${t('overview')}\n  \n  ## ${t('requirements')}\n  \n  ## ${t('architecture')}\n  \n  ## ${t('implementation')}\n  \n  ## ${t('testing')}\n  \n  ## ${t('deployment')}\n  \n  ## ${t('maintenance')}\n  `,
      isCustom: false,
    },
    {
      id: 'default_3',
      name: t('meetingMinutes'),
      content: `# ${t('meetingMinutesTitle')}\n  \n  ## ${t('date')}: ${new Date().toLocaleDateString()}\n  \n  ## ${t('participants')}\n  \n  ## ${t('agenda')}\n  \n  ## ${t('discussions')}\n  \n  ## ${t('decisions')}\n  \n  ## ${t('actionItems')}\n  \n  ## ${t('nextMeeting')}\n  `,
      isCustom: false,
    },
  ];

  // 加载和初始化模板
  useEffect(() => {
    const loadTemplatesFromStorage = () => {
      try {
        const savedTemplatesString = localStorage.getItem(
          LOCAL_STORAGE_TEMPLATES_KEY,
        );
        if (savedTemplatesString) {
          const loadedTemplates = JSON.parse(
            savedTemplatesString,
          ) as TemplateItem[];
          setTemplates(loadedTemplates);
          if (loadedTemplates.length > 0) {
            // 默认选中第一个模板，或之前选中的模板（如果需要更复杂的选中逻辑）
            const currentSelected = selectedTemplate || loadedTemplates[0].id;
            const foundSelected = loadedTemplates.find(
              (t) => t.id === currentSelected,
            );
            if (foundSelected) {
              setSelectedTemplate(foundSelected.id);
              setContent(foundSelected.content);
            } else if (loadedTemplates.length > 0) {
              setSelectedTemplate(loadedTemplates[0].id);
              setContent(loadedTemplates[0].content);
            } else {
              setContent(''); // 没有模板了
              setSelectedTemplate('');
            }
          } else {
            setContent(''); // 没有模板则清空内容
            setSelectedTemplate('');
          }
        } else {
          // localStorage中没有模板，初始化默认模板并存储
          const initialDefaults = getInitialDefaultTemplates();
          setTemplates(initialDefaults);
          localStorage.setItem(
            LOCAL_STORAGE_TEMPLATES_KEY,
            JSON.stringify(initialDefaults),
          );
          if (initialDefaults.length > 0) {
            setSelectedTemplate(initialDefaults[0].id);
            setContent(initialDefaults[0].content);
          }
        }
      } catch (error) {
        console.error('加载模板失败:', error);
        // 加载失败，可以尝试使用硬编码的默认值作为后备
        const fallbackDefaults = getInitialDefaultTemplates();
        setTemplates(fallbackDefaults);
        if (fallbackDefaults.length > 0) {
          setSelectedTemplate(fallbackDefaults[0].id);
          setContent(fallbackDefaults[0].content);
        }
      }
    };

    loadTemplatesFromStorage();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [t]); // t 作为依赖，确保语言切换时默认模板名称能正确初始化

  // 获取对话列表和加载草稿
  useEffect(() => {
    const fetchDialogs = async () => {
      // ... (省略，与模板无关)
      try {
        const authorization = localStorage.getItem('Authorization');
        if (!authorization) {
          console.log('未登录，跳过获取对话列表');
          return;
        }
        const response = await axios.get('/v1/dialog', {
          headers: { authorization },
        });
        if (response.data?.data?.length > 0) {
          setDialogId(response.data.data[0].id);
        }
      } catch (error) {
        console.error('获取对话列表失败:', error);
      }
    };

    const loadDraftContent = () => {
      try {
        const draftContent = localStorage.getItem('writeDraftContent');
        // 只有当 templates 加载完毕后，且当前 content 仍然为空时，才加载草稿
        // 避免草稿覆盖刚从选中模板加载的内容
        if (draftContent && !content && templates.length > 0) {
          // 或者，我们可以优先草稿，如果草稿存在，就不从选中模板加载内容
          // 当前逻辑是：模板内容优先，如果模板内容为空，则尝试加载草_稿
          // 修改为：如果选了模板，就用模板内容；如果没选模板（比如全删了），再看草稿
          const currentSelectedTemplate = templates.find(
            (temp) => temp.id === selectedTemplate,
          );
          if (!currentSelectedTemplate && draftContent) {
            setContent(draftContent);
          } else if (
            currentSelectedTemplate &&
            !currentSelectedTemplate.content &&
            draftContent
          ) {
            // 如果选中的模板内容为空，也加载草稿
            setContent(draftContent);
          }
          // 如果只想在完全没有模板内容被设置时加载草稿：
          // if (draftContent && !content) setContent(draftContent);
        } else if (
          draftContent &&
          !selectedTemplate &&
          templates.length === 0
        ) {
          // 如果没有模板，也没有选中的模板，则加载草稿
          setContent(draftContent);
        }
      } catch (error) {
        console.error('加载暂存内容失败:', error);
      }
    };

    fetchDialogs();
    // loadTemplatesFromStorage 已经在上面的useEffect中处理
    // 草稿加载应该在模板和其内容设置之后，或者有更明确的优先级
    if (
      templates.length > 0 ||
      localStorage.getItem(LOCAL_STORAGE_TEMPLATES_KEY)
    ) {
      // 确保模板已尝试加载
      loadDraftContent();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [templates, selectedTemplate]); // 当模板或选中模板变化时，重新评估是否加载草稿

  // 自动保存内容到localStorage
  useEffect(() => {
    const timer = setTimeout(() => {
      try {
        localStorage.setItem('writeDraftContent', content);
      } catch (error) {
        console.error('保存暂存内容失败:', error);
      }
    }, 1000);

    return () => clearTimeout(timer);
  }, [content]);

  // 处理模板选择
  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplate(templateId);
    const selectedTemplateItem = templates.find(
      (item) => item.id === templateId,
    );
    if (selectedTemplateItem) {
      setContent(selectedTemplateItem.content);
    }
  };

  // 保存自定义模板
  const handleSaveTemplate = () => {
    if (!templateName.trim()) {
      message.warning(t('enterTemplateName'));
      return;
    }
    if (!content.trim()) {
      message.warning(t('enterTemplateContent'));
      return;
    }

    const newTemplate: TemplateItem = {
      id: `custom_${Date.now()}`,
      name: templateName,
      content: content,
      isCustom: true,
    };

    try {
      const updatedTemplates = [...templates, newTemplate];
      setTemplates(updatedTemplates);
      localStorage.setItem(
        LOCAL_STORAGE_TEMPLATES_KEY,
        JSON.stringify(updatedTemplates),
      );

      message.success(t('templateSavedSuccess'));
      setIsTemplateModalVisible(false);
      setTemplateName('');
      setSelectedTemplate(newTemplate.id); // 选中新保存的模板
    } catch (error) {
      console.error('保存模板失败:', error);
      message.error(t('templateSavedFailed'));
    }
  };

  // 删除模板 (包括默认模板)
  const handleDeleteTemplate = (templateId: string) => {
    try {
      const updatedTemplates = templates.filter((t) => t.id !== templateId);
      setTemplates(updatedTemplates);
      localStorage.setItem(
        LOCAL_STORAGE_TEMPLATES_KEY,
        JSON.stringify(updatedTemplates),
      );

      if (selectedTemplate === templateId) {
        // 如果删除的是当前选中的模板
        if (updatedTemplates.length > 0) {
          // 切换到列表中的第一个模板
          setSelectedTemplate(updatedTemplates[0].id);
          setContent(updatedTemplates[0].content);
        } else {
          // 如果没有模板了，清空内容和选择
          setSelectedTemplate('');
          setContent('');
        }
      }
      message.success(t('templateDeletedSuccess'));
    } catch (error) {
      console.error('删除模板失败:', error);
      message.error(t('templateDeletedFailed'));
    }
  };

  // 实现保存为Word功能
  const handleSave = () => {
    const selectedTemplateItem = templates.find(
      (item) => item.id === selectedTemplate,
    );
    const baseName = selectedTemplateItem
      ? selectedTemplateItem.name
      : t('document'); // 如果没有选中模板，使用通用名称

    const today = new Date();
    const dateStr = `${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, '0')}${String(today.getDate()).padStart(2, '0')}`;
    const fileName = `${baseName}${dateStr}.docx`;

    const tokens = marked.lexer(content);
    const paragraphs: Paragraph[] = [];

    tokens.forEach((token) => {
      if (token.type === 'heading') {
        const headingToken = token as any;
        let headingType:
          | 'Heading1'
          | 'Heading2'
          | 'Heading3'
          | 'Heading4'
          | 'Heading5'
          | 'Heading6'
          | undefined;
        switch (headingToken.depth) {
          case 1:
            headingType = 'Heading1';
            break;
          case 2:
            headingType = 'Heading2';
            break;
          // ... (其他 case)
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
        const paraToken = token as any;
        paragraphs.push(
          new Paragraph({
            children: [new TextRun({ text: paraToken.text })],
            spacing: { after: 80 },
          }),
        );
      } else if (token.type === 'space') {
        paragraphs.push(new Paragraph({}));
      }
    });

    const doc = new Document({ sections: [{ children: paragraphs }] });
    Packer.toBlob(doc).then((blob) => {
      saveAs(blob, fileName);
    });
  };

  // ... renderEditor, renderPreview, renderContent, handleAiQuestionSubmit (这些函数基本不变)
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
          const target = e.target as HTMLTextAreaElement;
          setCursorPosition(target.selectionStart);
          setShowCursorIndicator(true);
        }}
        onKeyUp={(e) => {
          const target = e.target as HTMLTextAreaElement;
          setCursorPosition(target.selectionStart);
          setShowCursorIndicator(true);
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

      const initialCursorPos = cursorPosition;
      const initialContent = content;
      let beforeCursor = '';
      let afterCursor = '';

      if (initialCursorPos !== null && showCursorIndicator) {
        beforeCursor = initialContent.substring(0, initialCursorPos);
        afterCursor = initialContent.substring(initialCursorPos);
      }

      const controller = new AbortController();
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

        const conversationId =
          Math.random().toString(36).substring(2) + Date.now().toString(36);

        try {
          const createSessionResponse = await axios.post(
            'v1/conversation/set',
            {
              dialog_id: dialogId,
              name: '文档撰写对话',
              is_new: true,
              conversation_id: conversationId,
              message: [{ role: 'assistant', content: '新对话' }],
            },
            { headers: { authorization }, signal: controller.signal },
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

        const combinedQuestion = `${aiQuestion}\n\n当前文档内容：\n${content}`;
        console.log('发送问题到 AI 助手:', aiQuestion);
        let lastContent = '';

        try {
          const response = await axios.post(
            '/v1/conversation/completion',
            {
              conversation_id: conversationId,
              messages: [{ role: 'user', content: combinedQuestion }],
            },
            {
              timeout: aiAssistantConfig.api.timeout,
              headers: { authorization },
              signal: controller.signal,
            },
          );

          if (response.data) {
            const lines = response.data
              .split('\n')
              .filter((line: string) => line.trim());

            for (let i = 0; i < lines.length; i++) {
              try {
                const jsonStr = lines[i].replace('data:', '').trim();
                const jsonData = JSON.parse(jsonStr);

                if (jsonData.code === 0 && jsonData.data?.answer) {
                  const answer = jsonData.data.answer;
                  const cleanedAnswer = answer
                    .replace(/<think>[\s\S]*?<\/think>/g, '')
                    .trim();
                  const hasUnclosedThink =
                    cleanedAnswer.includes('<think>') &&
                    (!cleanedAnswer.includes('</think>') ||
                      cleanedAnswer.indexOf('<think>') >
                        cleanedAnswer.lastIndexOf('</think>'));

                  if (cleanedAnswer && !hasUnclosedThink) {
                    const newContentChunk = cleanedAnswer;
                    const incrementalContent = newContentChunk.substring(
                      lastContent.length,
                    );

                    if (incrementalContent) {
                      lastContent = newContentChunk;

                      if (initialCursorPos !== null && showCursorIndicator) {
                        const currentFullContent =
                          beforeCursor + newContentChunk + afterCursor;
                        setContent(currentFullContent);
                        const newPosition =
                          initialCursorPos + newContentChunk.length;
                        setCursorPosition(newPosition);
                        if (textAreaRef.current) {
                          setTimeout(() => {
                            if (textAreaRef.current) {
                              textAreaRef.current.focus();
                              textAreaRef.current.setSelectionRange(
                                newPosition,
                                newPosition,
                              );
                            }
                          }, 0);
                        }
                      } else {
                        setContent(initialContent + newContentChunk);
                      }
                    }
                  }
                }
              } catch (parseErr) {
                console.error('解析单行数据失败:', parseErr);
              }
              if (i < lines.length - 1) {
                await new Promise((resolve) => {
                  setTimeout(resolve, 10);
                });
              }
            }
          }
        } catch (error: any) {
          console.error('获取 AI 回答失败:', error);
          if (error.code === 'ECONNABORTED' || error.name === 'AbortError') {
            message.error('AI 助手响应超时，请稍后重试');
          } else {
            message.error('获取 AI 回答失败，请重试');
          }
        } finally {
          clearTimeout(timeoutId);
        }

        try {
          await axios.post(
            '/v1/conversation/rm',
            {
              conversation_ids: [conversationId],
              dialog_id: dialogId,
            },
            { headers: { authorization } },
          );
          console.log('临时会话已删除:', conversationId);
          if (textAreaRef.current) {
            textAreaRef.current.focus();
            if (cursorPosition !== null && showCursorIndicator) {
              setTimeout(() => {
                if (textAreaRef.current) {
                  textAreaRef.current.setSelectionRange(
                    cursorPosition,
                    cursorPosition,
                  );
                }
              }, 0);
            }
          }
        } catch (rmErr) {
          console.error('删除临时会话失败:', rmErr);
        }
      } catch (err) {
        console.error('AI 助手处理失败:', err);
        message.error('AI 助手处理失败，请重试');
      } finally {
        setIsAiLoading(false);
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
              <Typography.Title
                level={5}
                style={{ marginBottom: '8px', marginTop: 0 }}
              >
                {t('templateList')}
              </Typography.Title>
              <Button
                type="primary"
                size="small"
                style={{ marginTop: 8 }}
                onClick={() => setIsTemplateModalVisible(true)}
              >
                {t('saveCurrentAsTemplate')}
              </Button>
            </div>
          }
          dataSource={templates} // 数据源现在是动态从localStorage加载的
          locale={{ emptyText: t('noTemplatesAvailable') }}
          renderItem={(item) => (
            <List.Item
              actions={[
                <Popconfirm
                  key="delete"
                  title={t('confirmDeleteTemplate')}
                  onConfirm={() => handleDeleteTemplate(item.id)}
                  okText={t('confirm')}
                  cancelText={t('cancel')}
                >
                  <Button type="link" danger size="small">
                    {t('delete')}
                  </Button>
                </Popconfirm>,
              ]}
              style={{
                cursor: 'pointer',
                background: selectedTemplate === item.id ? '#f0f7ff' : 'none',
                borderRadius: 8,
                paddingLeft: 12,
              }}
              onClick={() => handleTemplateSelect(item.id)}
            >
              <span className="templateItemText">
                {item.name}
                {item.isCustom && (
                  <span style={{ color: '#1890ff', marginLeft: 4 }}>
                    ({t('customTemplateMarker')})
                  </span>
                )}
                {/* 可以根据 item.id.startsWith('default_') 来判断是否是初始默认模板并给予不同样式 */}
              </span>
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
                  <div>{t('aiLoadingMessage')}</div>
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

      <Modal
        title={t('saveAsCustomTemplateTitle')}
        open={isTemplateModalVisible}
        onOk={handleSaveTemplate}
        onCancel={() => {
          setIsTemplateModalVisible(false);
          setTemplateName('');
        }}
        okText={t('saveTemplate')}
        cancelText={t('cancel')}
      >
        {/* (Modal 内容不变) */}
        <div style={{ marginBottom: 16 }}>
          <label>{t('templateNameLabel')}:</label>
          <Input
            placeholder={t('templateNamePlaceholder')}
            value={templateName}
            onChange={(e) => setTemplateName(e.target.value)}
            style={{ marginTop: 8 }}
          />
        </div>
        <div>
          <label>{t('templateContentPreviewLabel')}:</label>
          <Input.TextArea
            value={content}
            disabled
            rows={6}
            style={{ marginTop: 8 }}
          />
        </div>
      </Modal>
    </Layout>
  );
};

export default Write;
