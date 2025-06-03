import HightLightMarkdown from '@/components/highlight-markdown';
import { useTranslate } from '@/hooks/common-hooks';
import { DeleteOutlined } from '@ant-design/icons';
import {
  Button,
  Card,
  Divider,
  Flex,
  Form,
  Input,
  Layout,
  List,
  message,
  Modal,
  Popconfirm,
  Select,
  Slider,
  Space,
  Typography,
} from 'antd';
import axios from 'axios';
import {
  AlignmentType,
  Document,
  HeadingLevel,
  Packer,
  Paragraph,
  TextRun,
} from 'docx';
import { saveAs } from 'file-saver';
import { marked, Token, Tokens } from 'marked';
import { useCallback, useEffect, useRef, useState } from 'react';

const { Sider, Content } = Layout;
const { Option } = Select;
const aiAssistantConfig = { api: { timeout: 30000 } };

const LOCAL_STORAGE_TEMPLATES_KEY = 'userWriteTemplates_v4_no_restore_final';
const LOCAL_STORAGE_INIT_FLAG_KEY =
  'userWriteTemplates_initialized_v4_no_restore_final';

interface TemplateItem {
  id: string;
  name: string;
  content: string;
  isCustom?: boolean;
}
interface KnowledgeBaseItem {
  id: string;
  name: string;
}

type MarkedHeadingToken = Tokens.Heading;
type MarkedParagraphToken = Tokens.Paragraph;
type MarkedListItem = Tokens.ListItem;
type MarkedListToken = Tokens.List;
type MarkedSpaceToken = Tokens.Space;

const Write = () => {
  const { t } = useTranslate('write');
  const [content, setContent] = useState('');
  const [aiQuestion, setAiQuestion] = useState('');
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [dialogId] = useState('');
  const [cursorPosition, setCursorPosition] = useState<number | null>(null);
  const [showCursorIndicator, setShowCursorIndicator] = useState(false);
  const textAreaRef = useRef<HTMLTextAreaElement>(null);

  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [isTemplateModalVisible, setIsTemplateModalVisible] = useState(false);
  const [templateName, setTemplateName] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [viewMode, setViewMode] = useState<'edit' | 'preview' | 'split'>(
    'split',
  );

  const [selectedKnowledgeBases, setSelectedKnowledgeBases] = useState<
    string[]
  >([]);
  const [similarityThreshold, setSimilarityThreshold] = useState<number>(0.7);
  const [keywordSimilarityWeight, setKeywordSimilarityWeight] =
    useState<number>(0.5);
  const [modelTemperature, setModelTemperature] = useState<number>(0.7);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBaseItem[]>([]);
  const [isLoadingKbs, setIsLoadingKbs] = useState(false);

  const getInitialDefaultTemplateDefinitions = useCallback(
    (): TemplateItem[] => [
      {
        id: 'default_1_v4f',
        name: t('defaultTemplate'),
        content: `# ${t('defaultTemplateTitle')}\n ## ${t('introduction')}\n  ## ${t('mainContent')}\n  \n  ## ${t('conclusion')}\n  `,
        isCustom: false,
      },
      {
        id: 'default_2_v4f',
        name: t('technicalDoc'),
        content: `# ${t('technicalDocTitle')}\n  \n  ## ${t('overview')}\n  \n  ## ${t('requirements')}\n  \n  ## ${t('architecture')}\n  \n  ## ${t('implementation')}\n  \n  ## ${t('testing')}\n  \n  ## ${t('deployment')}\n  \n  ## ${t('maintenance')}\n  `,
        isCustom: false,
      },
      {
        id: 'default_3_v4f',
        name: t('meetingMinutes'),
        content: `# ${t('meetingMinutesTitle')}\n  \n  ## ${t('date')}: ${new Date().toLocaleDateString()}\n  \n  ## ${t('participants')}\n  \n  ## ${t('agenda')}\n  \n  ## ${t('discussions')}\n  \n  ## ${t('decisions')}\n  \n  ## ${t('actionItems')}\n  \n  ## ${t('nextMeeting')}\n  `,
        isCustom: false,
      },
    ],
    [t],
  );

  const loadOrInitializeTemplates = useCallback(() => {
    try {
      const initialized = localStorage.getItem(LOCAL_STORAGE_INIT_FLAG_KEY);
      let currentTemplates: TemplateItem[] = [];
      if (initialized === 'true') {
        const savedTemplatesString = localStorage.getItem(
          LOCAL_STORAGE_TEMPLATES_KEY,
        );
        currentTemplates = savedTemplatesString
          ? JSON.parse(savedTemplatesString)
          : getInitialDefaultTemplateDefinitions();
        if (!savedTemplatesString) {
          localStorage.setItem(
            LOCAL_STORAGE_TEMPLATES_KEY,
            JSON.stringify(currentTemplates),
          );
        }
      } else {
        currentTemplates = getInitialDefaultTemplateDefinitions();
        localStorage.setItem(
          LOCAL_STORAGE_TEMPLATES_KEY,
          JSON.stringify(currentTemplates),
        );
        localStorage.setItem(LOCAL_STORAGE_INIT_FLAG_KEY, 'true');
      }
      setTemplates(currentTemplates);
      if (currentTemplates.length > 0 && !selectedTemplate) {
        setSelectedTemplate(currentTemplates[0].id);
        setContent(currentTemplates[0].content);
      } else if (selectedTemplate) {
        const current = currentTemplates.find(
          (ts) => ts.id === selectedTemplate,
        );
        if (current) setContent(current.content);
        else if (currentTemplates.length > 0) {
          setSelectedTemplate(currentTemplates[0].id);
          setContent(currentTemplates[0].content);
        } else {
          setSelectedTemplate('');
          setContent('');
        }
      }
    } catch (error) {
      console.error('加载或初始化模板失败:', error);
      message.error(t('loadTemplatesFailedError'));
      const fallbackDefaults = getInitialDefaultTemplateDefinitions();
      setTemplates(fallbackDefaults);
      if (fallbackDefaults.length > 0) {
        setSelectedTemplate(fallbackDefaults[0].id);
        setContent(fallbackDefaults[0].content);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [t, getInitialDefaultTemplateDefinitions]);

  useEffect(() => {
    loadOrInitializeTemplates();
  }, [loadOrInitializeTemplates]);

  useEffect(() => {
    const fetchKbs = async () => {
      const authorization = localStorage.getItem('Authorization');
      if (!authorization) {
        setKnowledgeBases([]);
        return;
      }
      setIsLoadingKbs(true);
      try {
        await new Promise((resolve) => {
          setTimeout(resolve, 500);
        });
        const mockKbs: KnowledgeBaseItem[] = [
          {
            id: 'kb_default',
            name: t('defaultKnowledgeBase', { defaultValue: '默认知识库' }),
          },
          {
            id: 'kb_tech',
            name: t('technicalDocsKnowledgeBase', {
              defaultValue: '技术文档知识库',
            }),
          },
          {
            id: 'kb_product',
            name: t('productInfoKnowledgeBase', {
              defaultValue: '产品信息知识库',
            }),
          },
          {
            id: 'kb_marketing',
            name: t('marketingMaterialsKB', { defaultValue: '市场营销材料库' }),
          },
          {
            id: 'kb_legal',
            name: t('legalDocumentsKB', { defaultValue: '法律文件库' }),
          },
        ];
        setKnowledgeBases(mockKbs);
      } catch (error) {
        console.error('获取知识库失败:', error);
        message.error(t('fetchKnowledgeBaseFailed'));
        setKnowledgeBases([]);
      } finally {
        setIsLoadingKbs(false);
      }
    };
    fetchKbs();
  }, [t]);

  useEffect(() => {
    const loadDraftContent = () => {
      try {
        const draftContent = localStorage.getItem('writeDraftContent');
        if (
          draftContent &&
          !content &&
          (!selectedTemplate ||
            templates.find((t) => t.id === selectedTemplate)?.content === '')
        ) {
          setContent(draftContent);
        }
      } catch (error) {
        console.error('加载暂存内容失败:', error);
      }
    };
    if (localStorage.getItem(LOCAL_STORAGE_INIT_FLAG_KEY) === 'true') {
      loadDraftContent();
    }
  }, [content, selectedTemplate, templates]);

  useEffect(() => {
    const timer = setTimeout(
      () => localStorage.setItem('writeDraftContent', content),
      1000,
    );
    return () => clearTimeout(timer);
  }, [content]);

  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplate(templateId);
    const item = templates.find((t) => t.id === templateId);
    if (item) setContent(item.content);
  };

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
      content,
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
      setSelectedTemplate(newTemplate.id);
    } catch (error) {
      console.error('保存模板失败:', error);
      message.error(t('templateSavedFailed'));
    }
  };

  const handleDeleteTemplate = (templateId: string) => {
    try {
      const updatedTemplates = templates.filter((t) => t.id !== templateId);
      setTemplates(updatedTemplates);
      localStorage.setItem(
        LOCAL_STORAGE_TEMPLATES_KEY,
        JSON.stringify(updatedTemplates),
      );
      if (selectedTemplate === templateId) {
        if (updatedTemplates.length > 0) {
          setSelectedTemplate(updatedTemplates[0].id);
          setContent(updatedTemplates[0].content);
        } else {
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

  const handleAiQuestionSubmit = async (
    e: React.KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!aiQuestion.trim()) {
        message.warning(t('enterYourQuestion'));
        return;
      }

      setIsAiLoading(true);
      const initialCursorPos = cursorPosition;
      const originalContent = content;
      let beforeCursor = '',
        afterCursor = '';
      if (initialCursorPos !== null && showCursorIndicator) {
        beforeCursor = originalContent.substring(0, initialCursorPos);
        afterCursor = originalContent.substring(initialCursorPos);
      }
      const controller = new AbortController();
      const timeoutId = setTimeout(
        () => controller.abort(),
        aiAssistantConfig.api.timeout || 30000,
      );
      try {
        const authorization = localStorage.getItem('Authorization');
        if (!authorization) {
          message.error(t('loginRequiredError'));
          setIsAiLoading(false);
          return;
        }
        const conversationId =
          Math.random().toString(36).substring(2) + Date.now().toString(36);
        await axios.post(
          'v1/conversation/set',
          {
            name: '文档撰写对话',
            is_new: true,
            conversation_id: conversationId,
            message: [{ role: 'assistant', content: '新对话' }],
          },
          { headers: { authorization }, signal: controller.signal },
        );
        const combinedQuestion = `${aiQuestion}\n\n${t('currentDocumentContextLabel')}:\n${originalContent}`;
        let lastReceivedContent = '';
        const response = await axios.post(
          '/v1/conversation/completion',
          {
            conversation_id: conversationId,
            messages: [{ role: 'user', content: combinedQuestion }],
            knowledge_base_ids:
              selectedKnowledgeBases.length > 0
                ? selectedKnowledgeBases
                : undefined,
            similarity_threshold: similarityThreshold,
            keyword_similarity_weight: keywordSimilarityWeight,
            temperature: modelTemperature,
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
                const answerChunk = jsonData.data.answer;
                const cleanedAnswerChunk = answerChunk
                  .replace(/<think>[\s\S]*?<\/think>/g, '')
                  .trim();
                const hasUnclosedThink =
                  cleanedAnswerChunk.includes('<think>') &&
                  (!cleanedAnswerChunk.includes('</think>') ||
                    cleanedAnswerChunk.indexOf('<think>') >
                      cleanedAnswerChunk.lastIndexOf('</think>'));
                if (cleanedAnswerChunk && !hasUnclosedThink) {
                  const incrementalContent = cleanedAnswerChunk.substring(
                    lastReceivedContent.length,
                  );
                  if (incrementalContent) {
                    lastReceivedContent = cleanedAnswerChunk;
                    let newFullContent,
                      newCursorPosAfterInsertion = cursorPosition;
                    if (initialCursorPos !== null && showCursorIndicator) {
                      newFullContent =
                        beforeCursor + cleanedAnswerChunk + afterCursor;
                      newCursorPosAfterInsertion =
                        initialCursorPos + cleanedAnswerChunk.length;
                    } else {
                      newFullContent = originalContent + cleanedAnswerChunk;
                      newCursorPosAfterInsertion = newFullContent.length;
                    }
                    setContent(newFullContent);
                    setCursorPosition(newCursorPosAfterInsertion);
                    setTimeout(() => {
                      if (textAreaRef.current) {
                        textAreaRef.current.focus();
                        textAreaRef.current.setSelectionRange(
                          newCursorPosAfterInsertion!,
                          newCursorPosAfterInsertion!,
                        );
                      }
                    }, 0);
                  }
                }
              }
            } catch (parseErr) {
              console.error('解析单行数据失败:', parseErr);
            }
            if (i < lines.length - 1)
              await new Promise((resolve) => {
                setTimeout(resolve, 10);
              });
          }
        }
        await axios.post(
          '/v1/conversation/rm',
          { conversation_ids: [conversationId], dialog_id: dialogId },
          { headers: { authorization } },
        );
      } catch (error: any) {
        console.error('AI助手处理失败:', error);
        if (error.code === 'ECONNABORTED' || error.name === 'AbortError') {
          message.error(t('aiRequestTimeoutError'));
        } else if (error.response?.data?.message) {
          message.error(
            `${t('aiRequestFailedError')}: ${error.response.data.message}`,
          );
        } else {
          message.error(t('aiRequestFailedError'));
        }
      } finally {
        clearTimeout(timeoutId);
        setIsAiLoading(false);
        setAiQuestion('');
        if (textAreaRef.current) textAreaRef.current.focus();
      }
    }
  };

  const handleSave = () => {
    const selectedTemplateItem = templates.find(
      (item) => item.id === selectedTemplate,
    );
    const baseName = selectedTemplateItem
      ? selectedTemplateItem.name
      : t('document', { defaultValue: '文档' });
    const today = new Date();
    const dateStr = `${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, '0')}${String(today.getDate()).padStart(2, '0')}`;
    const fileName = `${baseName}_${dateStr}.docx`;

    if (!content.trim()) {
      message.warning(
        t('emptyContentCannotExport', { defaultValue: '内容为空，无法导出' }),
      );
      return;
    }

    try {
      const tokens = marked.lexer(content) as Token[];
      const paragraphs: Paragraph[] = [];

      function parseTokensToRuns(
        inlineTokens: Tokens.Generic[] | undefined,
      ): TextRun[] {
        const runs: TextRun[] = [];
        if (!inlineTokens) return runs;

        inlineTokens.forEach((token) => {
          if (token.type === 'text') {
            runs.push(new TextRun(token.raw)); // Use raw for exact text
          } else if (
            token.type === 'strong' &&
            'text' in token &&
            typeof token.text === 'string'
          ) {
            runs.push(new TextRun({ text: token.text, bold: true }));
          } else if (
            token.type === 'em' &&
            'text' in token &&
            typeof token.text === 'string'
          ) {
            runs.push(new TextRun({ text: token.text, italics: true }));
          } else if (
            token.type === 'codespan' &&
            'text' in token &&
            typeof token.text === 'string'
          ) {
            runs.push(new TextRun({ text: token.text, style: 'Consolas' }));
          } else if (
            token.type === 'del' &&
            'text' in token &&
            typeof token.text === 'string'
          ) {
            runs.push(new TextRun({ text: token.text, strike: true }));
          } else if (
            token.type === 'link' &&
            'text' in token &&
            typeof token.text === 'string' &&
            'href' in token &&
            typeof token.href === 'string'
          ) {
            runs.push(new TextRun({ text: token.text, style: 'Hyperlink' }));
          } else if ('raw' in token) {
            runs.push(new TextRun(token.raw));
          }
        });
        return runs;
      }

      tokens.forEach((token) => {
        if (token.type === 'heading') {
          const headingToken = token as MarkedHeadingToken;
          let docxHeadingLevel: (typeof HeadingLevel)[keyof typeof HeadingLevel];
          switch (headingToken.depth) {
            case 1:
              docxHeadingLevel = HeadingLevel.HEADING_1;
              break;
            case 2:
              docxHeadingLevel = HeadingLevel.HEADING_2;
              break;
            case 3:
              docxHeadingLevel = HeadingLevel.HEADING_3;
              break;
            case 4:
              docxHeadingLevel = HeadingLevel.HEADING_4;
              break;
            case 5:
              docxHeadingLevel = HeadingLevel.HEADING_5;
              break;
            case 6:
              docxHeadingLevel = HeadingLevel.HEADING_6;
              break;
            default:
              docxHeadingLevel = HeadingLevel.HEADING_1;
          }
          paragraphs.push(
            new Paragraph({
              children: parseTokensToRuns(
                headingToken.tokens ||
                  ([
                    {
                      type: 'text',
                      raw: headingToken.text,
                      text: headingToken.text,
                    },
                  ] as any),
              ),
              heading: docxHeadingLevel,
              spacing: {
                after: 200 - headingToken.depth * 20,
                before: headingToken.depth === 1 ? 0 : 100,
              },
            }),
          );
        } else if (token.type === 'paragraph') {
          const paraToken = token as MarkedParagraphToken;
          const runs = parseTokensToRuns(paraToken.tokens);
          paragraphs.push(
            new Paragraph({
              children: runs.length > 0 ? runs : [new TextRun('')],
              spacing: { after: 120 },
            }),
          );
        } else if (token.type === 'list') {
          const listToken = token as MarkedListToken;
          listToken.items.forEach((listItem: MarkedListItem) => {
            const itemRuns = parseTokensToRuns(listItem.tokens);
            paragraphs.push(
              new Paragraph({
                children: itemRuns.length > 0 ? itemRuns : [new TextRun('')],
                bullet: listToken.ordered ? undefined : { level: 0 },
                numbering: listToken.ordered
                  ? { reference: 'default-numbering', level: 0 }
                  : undefined,
              }),
            );
          });
          paragraphs.push(new Paragraph({ spacing: { after: 80 } }));
        } else if (token.type === 'space') {
          const spaceToken = token as MarkedSpaceToken;
          const newlines = (spaceToken.raw.match(/\n/g) || []).length;
          if (newlines > 1) {
            for (let i = 0; i < newlines; i++)
              paragraphs.push(new Paragraph({}));
          } else {
            paragraphs.push(new Paragraph({ spacing: { after: 80 } }));
          }
        }
      });

      if (paragraphs.length === 0 && content.trim()) {
        paragraphs.push(new Paragraph({ children: [new TextRun(content)] }));
      }

      const doc = new Document({
        numbering: {
          config: [
            {
              reference: 'default-numbering',
              levels: [
                {
                  level: 0,
                  format: 'decimal',
                  text: '%1.',
                  alignment: AlignmentType.LEFT,
                },
              ],
            },
          ],
        },
        sections: [{ properties: {}, children: paragraphs }],
      });

      Packer.toBlob(doc)
        .then((blob) => {
          saveAs(blob, fileName);
          message.success(
            t('exportSuccess', { defaultValue: '文档导出成功!' }),
          );
        })
        .catch((packError) => {
          console.error('Error packing document: ', packError);
          message.error(
            t('exportFailedError', {
              defaultValue: '文档导出失败，请检查控制台日志。',
            }),
          );
        });
    } catch (error) {
      console.error('Error generating Word document: ', error);
      message.error(
        t('exportProcessError', { defaultValue: '处理文档导出时发生错误。' }),
      );
    }
  };

  const renderEditor = () => (
    <Input.TextArea
      ref={textAreaRef}
      style={{
        height: '100%',
        width: '100%',
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
  );
  const renderPreview = () => (
    <div
      style={{
        height: '100%',
        width: '100%',
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
        return (
          <div style={{ height: '100%', width: '100%' }}>{renderEditor()}</div>
        );
      case 'preview':
        return (
          <div style={{ height: '100%', width: '100%' }}>{renderPreview()}</div>
        );
      case 'split':
      default:
        return (
          <Flex style={{ height: '100%', width: '100%' }}>
            <div
              style={{
                flex: '1 1 50%',
                borderRight: '1px solid #f0f0f0',
                height: '100%',
                overflow: 'hidden',
              }}
            >
              {renderEditor()}
            </div>
            <div
              style={{ flex: '1 1 50%', height: '100%', overflow: 'hidden' }}
            >
              {renderPreview()}
            </div>
          </Flex>
        );
    }
  };

  return (
    <Layout
      style={{
        display: 'flex',
        flexDirection: 'row',
        overflow: 'hidden',
        flexGrow: 1,
      }}
    >
      <Sider
        width={320}
        theme="light"
        style={{
          borderRight: '1px solid #f0f0f0',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div
          style={{
            padding: '16px 16px 0 16px',
            height: '65%',
            minHeight: '250px',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <Typography.Title
            level={5}
            style={{ textAlign: 'center', marginBottom: 12, flexShrink: 0 }}
          >
            {t('templateList')}
          </Typography.Title>
          <Space
            direction="vertical"
            style={{ width: '100%', marginBottom: 16, flexShrink: 0 }}
          >
            <Button
              type="primary"
              block
              onClick={() => setIsTemplateModalVisible(true)}
            >
              {t('saveCurrentAsTemplate')}
            </Button>
          </Space>
          <div
            style={{
              flexGrow: 1,
              overflowY: 'auto',
              border: '1px solid #f0f0f0',
              borderRadius: '4px',
            }}
          >
            <List
              dataSource={templates}
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
                      <Button
                        type="text"
                        danger
                        icon={<DeleteOutlined />}
                        size="small"
                      />
                    </Popconfirm>,
                  ]}
                  style={{
                    cursor: 'pointer',
                    background:
                      selectedTemplate === item.id ? '#e6f7ff' : 'transparent',
                    padding: '8px 12px',
                    borderBottom: '1px solid #f0f0f0',
                  }}
                  onClick={() => handleTemplateSelect(item.id)}
                >
                  <Typography.Text
                    ellipsis={{ tooltip: item.name }}
                    style={{ flexGrow: 1, marginRight: 8 }}
                  >
                    {item.name}
                  </Typography.Text>
                  {item.isCustom && (
                    <Typography.Text
                      type="secondary"
                      style={{ fontSize: '0.85em', flexShrink: 0 }}
                    >
                      ({t('customTemplateMarker')})
                    </Typography.Text>
                  )}
                </List.Item>
              )}
            />
          </div>
        </div>
        <Divider style={{ margin: '16px 0', borderTopWidth: '1px' }} />
        <div
          style={{
            padding: '0 16px 16px 16px',
            flexGrow: 1,
            overflowY: 'auto',
          }}
        >
          <Typography.Title
            level={5}
            style={{ textAlign: 'center', marginBottom: 12, flexShrink: 0 }}
          >
            {t('modelConfigurationTitle', { defaultValue: '模型配置' })}
          </Typography.Title>
          <Form layout="vertical" component={false} size="small">
            <Form.Item
              label={t('knowledgeBaseLabel', {
                defaultValue: '知识库 (可多选)',
              })}
              style={{ marginBottom: 12 }}
            >
              <Select
                mode="multiple"
                placeholder={t('knowledgeBasePlaceholderMulti', {
                  defaultValue: '选择一个或多个知识库',
                })}
                value={selectedKnowledgeBases}
                onChange={setSelectedKnowledgeBases}
                allowClear
                style={{ width: '100%' }}
                loading={isLoadingKbs}
                filterOption={(input, option) =>
                  (option?.children?.toString() ?? '')
                    .toLowerCase()
                    .includes(input.toLowerCase())
                }
                maxTagCount="responsive"
                notFoundContent={
                  isLoadingKbs ? null : t('noKnowledgeBaseFound')
                }
              >
                {knowledgeBases.map((kb) => (
                  <Option key={kb.id} value={kb.id}>
                    {kb.name}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item
              label={`${t('similarityThresholdLabel')}: ${similarityThreshold.toFixed(2)}`}
              style={{ marginBottom: 12 }}
            >
              <Slider
                min={0}
                max={1}
                step={0.01}
                value={similarityThreshold}
                onChange={setSimilarityThreshold}
                tooltip={{ formatter: (value) => `${value?.toFixed(2)}` }}
              />
            </Form.Item>
            <Form.Item
              label={`${t('keywordSimilarityWeightLabel')}: ${keywordSimilarityWeight.toFixed(2)}`}
              style={{ marginBottom: 12 }}
            >
              <Slider
                min={0}
                max={1}
                step={0.01}
                value={keywordSimilarityWeight}
                onChange={setKeywordSimilarityWeight}
                tooltip={{ formatter: (value) => `${value?.toFixed(2)}` }}
              />
            </Form.Item>
            <Form.Item
              label={`${t('modelTemperatureLabel')}: ${modelTemperature.toFixed(2)}`}
              style={{ marginBottom: 0 }}
            >
              <Slider
                min={0}
                max={2}
                step={0.01}
                value={modelTemperature}
                onChange={setModelTemperature}
                tooltip={{ formatter: (value) => `${value?.toFixed(2)}` }}
              />
            </Form.Item>
          </Form>
        </div>
      </Sider>
      <Content
        style={{
          flexGrow: 1,
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <Flex
          vertical
          style={{
            flexGrow: 1,
            gap: 16,
            height: '100%',
            padding: '24px',
            overflow: 'hidden',
          }}
        >
          <Flex
            justify="space-between"
            align="center"
            style={{ flexShrink: 0 }}
          >
            <Typography.Title level={3} style={{ margin: 0 }}>
              {t('writeDocument')}
            </Typography.Title>
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
                {t('saveToWord', { defaultValue: '导出为Word' })}
              </Button>
            </Space>
          </Flex>
          <Card
            bodyStyle={{
              padding: 0,
              height: '100%',
              overflow: 'hidden',
              display: 'flex',
            }}
            style={{
              flexGrow: 1,
              display: 'flex',
              flexDirection: 'column',
              minHeight: 0,
            }}
          >
            {renderContent()}
          </Card>
          <Card
            title={t('aiAssistant')}
            bodyStyle={{
              padding: '12px',
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
            }}
            style={{ flexShrink: 0 }}
          >
            {isAiLoading && (
              <div style={{ textAlign: 'center', marginBottom: 8 }}>
                {t('aiLoadingMessage')}...
              </div>
            )}
            <Input.TextArea
              placeholder={t('askAI')}
              autoSize={{ minRows: 2, maxRows: 5 }}
              value={aiQuestion}
              onChange={(e) => setAiQuestion(e.target.value)}
              onKeyDown={handleAiQuestionSubmit}
              disabled={isAiLoading}
            />
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
        <Form layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label={t('templateNameLabel')} required>
            <Input
              placeholder={t('templateNamePlaceholder')}
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
            />
          </Form.Item>
          <Form.Item label={t('templateContentPreviewLabel')}>
            <Input.TextArea value={content} disabled rows={6} />
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  );
};

export default Write;
