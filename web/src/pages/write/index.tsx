import HightLightMarkdown from '@/components/highlight-markdown';
import { useTranslate } from '@/hooks/common-hooks';
import {
  useFetchKnowledgeList,
  useSendMessageWithSse,
  useUploadImage,
} from '@/hooks/write-hooks';

import { DeleteOutlined, UploadOutlined } from '@ant-design/icons';
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
import {
  AlignmentType,
  Document,
  HeadingLevel,
  ImageRun,
  Packer,
  Paragraph,
  TextRun,
} from 'docx';
import { saveAs } from 'file-saver';
import { marked, Token, Tokens } from 'marked';
import { useCallback, useEffect, useRef, useState } from 'react';

const { Sider, Content } = Layout;
const { Option } = Select;

// --- KEY DEFINITIONS ---
const LOCAL_STORAGE_TEMPLATES_KEY = 'userWriteTemplates_v4_no_restore_final';
const LOCAL_STORAGE_INIT_FLAG_KEY =
  'userWriteTemplates_initialized_v4_no_restore_final';
// 为草稿内容定义一个清晰的 key
const LOCAL_STORAGE_DRAFT_KEY = 'writeDraftContent';

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
type MarkedImageToken = Tokens.Image;
type MarkedListItem = Tokens.ListItem;
type MarkedListToken = Tokens.List;

const INSERTION_MARKER = '';

const Write = () => {
  const { t } = useTranslate('write');
  const [content, setContent] = useState('');
  const [aiQuestion, setAiQuestion] = useState('');
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [dialogId] = useState('');
  const [cursorPosition, setCursorPosition] = useState<number | null>(null);
  const [showCursorIndicator, setShowCursorIndicator] = useState(false);
  const textAreaRef = useRef<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
  const [similarityThreshold, setSimilarityThreshold] = useState<number>(0.2);
  const [keywordSimilarityWeight, setKeywordSimilarityWeight] =
    useState<number>(0.7);
  const [modelTemperature, setModelTemperature] = useState<number>(1.0);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBaseItem[]>([]);
  const [isLoadingKbs, setIsLoadingKbs] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);

  const [currentStreamedAiOutput, setCurrentStreamedAiOutput] = useState('');
  const contentBeforeAiInsertionRef = useRef('');
  const contentAfterAiInsertionRef = useRef('');
  const aiInsertionStartPosRef = useRef<number | null>(null);

  const { list: knowledgeList, loading: isLoadingKnowledgeList } =
    useFetchKnowledgeList(true);

  const {
    send: sendMessage,
    answer,
    done,
    stopOutputMessage,
  } = useSendMessageWithSse();

  const { uploadImage } = useUploadImage();

  const getInitialDefaultTemplateDefinitions = useCallback(
    (): TemplateItem[] => [
      {
        id: 'default_1_v4f',
        name: t('defaultTemplate'),
        content: `# ${t('defaultTemplateTitle')}\n \n ## ${t('introduction')}\n \n ## ${t('mainContent')}\n \n ## ${t('conclusion')}\n  `,
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

  //初始化逻辑
  useEffect(() => {
    // 定义一个内部函数来处理初始化，避免在 useEffect 中直接使用 async
    const initialize = () => {
      try {
        // 加载或初始化模板列表
        const initialized = localStorage.getItem(LOCAL_STORAGE_INIT_FLAG_KEY);
        let currentTemplates: TemplateItem[] = [];
        if (initialized === 'true') {
          const savedTemplatesString = localStorage.getItem(
            LOCAL_STORAGE_TEMPLATES_KEY,
          );
          currentTemplates = savedTemplatesString
            ? JSON.parse(savedTemplatesString)
            : getInitialDefaultTemplateDefinitions();
        } else {
          currentTemplates = getInitialDefaultTemplateDefinitions();
          localStorage.setItem(
            LOCAL_STORAGE_TEMPLATES_KEY,
            JSON.stringify(currentTemplates),
          );
          localStorage.setItem(LOCAL_STORAGE_INIT_FLAG_KEY, 'true');
        }
        setTemplates(currentTemplates);

        // 设定编辑器初始内容
        // 优先级 1: 尝试从 localStorage 加载上次的草稿
        const draftContent = localStorage.getItem(LOCAL_STORAGE_DRAFT_KEY);

        if (draftContent !== null) {
          // 如果存在草稿，无论模板是什么，都优先恢复草稿
          setContent(draftContent);
        } else if (currentTemplates.length > 0) {
          // 优先级 2: 如果没有草稿，则加载第一个模板作为初始内容
          const initialTemplate = currentTemplates[0];
          setSelectedTemplate(initialTemplate.id);
          setContent(initialTemplate.content);
        }
        // 如果既没有草稿也没有模板，内容将保持为空字符串
      } catch (error) {
        console.error('加载或初始化模板与内容失败:', error);
        message.error(t('loadTemplatesFailedError'));
        // 出现错误时的回退逻辑
        const fallbackDefaults = getInitialDefaultTemplateDefinitions();
        setTemplates(fallbackDefaults);
        if (fallbackDefaults.length > 0) {
          setSelectedTemplate(fallbackDefaults[0].id);
          setContent(fallbackDefaults[0].content);
        }
      }
    };

    initialize();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // <-- 使用空依赖数组，确保此 effect 只在组件首次挂载时运行一次！

  // 在 content 变化时，自动保存草稿到 localStorage
  useEffect(() => {
    // 使用防抖技术，避免过于频繁地写入 localStorage
    const timer = setTimeout(() => {
      // 只有在 content 不是初始空状态时才保存，避免覆盖有意义的草稿为空内容
      if (content) {
        localStorage.setItem(LOCAL_STORAGE_DRAFT_KEY, content);
      }
    }, 1000); // 延迟1秒保存

    // 组件卸载或 content 更新时，清除上一个计时器
    return () => clearTimeout(timer);
  }, [content]);

  // 将 knowledgeList 数据同步到 knowledgeBases 状态
  useEffect(() => {
    if (knowledgeList && knowledgeList.length > 0) {
      setKnowledgeBases(
        knowledgeList.map((kb) => ({
          id: kb.id,
          name: kb.name,
        })),
      );
      setIsLoadingKbs(isLoadingKnowledgeList);
    }
  }, [knowledgeList, isLoadingKnowledgeList]);

  // --- 调整流式响应处理逻辑 ---
  useEffect(() => {
    if (isStreaming && answer && answer.answer) {
      setCurrentStreamedAiOutput(answer.answer);
    }
  }, [isStreaming, answer]);

  useEffect(() => {
    if (done) {
      setIsStreaming(false);
      setIsAiLoading(false);
      let processedAiOutput = currentStreamedAiOutput;
      if (processedAiOutput) {
        processedAiOutput = processedAiOutput.replace(
          /<think>.*?<\/think>/gs,
          '',
        );
      }

      setContent((prevContent) => {
        if (aiInsertionStartPosRef.current !== null) {
          const finalContent =
            contentBeforeAiInsertionRef.current +
            processedAiOutput +
            contentAfterAiInsertionRef.current;
          return finalContent;
        }
        return prevContent;
      });

      if (
        textAreaRef.current?.resizableTextArea?.textArea &&
        aiInsertionStartPosRef.current !== null
      ) {
        const newCursorPos =
          aiInsertionStartPosRef.current + processedAiOutput.length;
        textAreaRef.current.resizableTextArea.textArea.selectionStart =
          newCursorPos;
        textAreaRef.current.resizableTextArea.textArea.selectionEnd =
          newCursorPos;
        textAreaRef.current.resizableTextArea.textArea.focus();
        setCursorPosition(newCursorPos);
      }

      setCurrentStreamedAiOutput('');
      contentBeforeAiInsertionRef.current = '';
      contentAfterAiInsertionRef.current = '';
      aiInsertionStartPosRef.current = null;
      setShowCursorIndicator(true);
    }
  }, [done, currentStreamedAiOutput]);

  useEffect(() => {
    if (isStreaming && aiInsertionStartPosRef.current !== null) {
      setContent(
        contentBeforeAiInsertionRef.current +
          currentStreamedAiOutput +
          contentAfterAiInsertionRef.current,
      );
      setCursorPosition(
        aiInsertionStartPosRef.current + currentStreamedAiOutput.length,
      );
    }
  }, [currentStreamedAiOutput, isStreaming]); // 移除了 aiInsertionStartPosRef 的依赖

  // 当用户主动选择一个模板时，用模板内容覆盖当前编辑器内容
  const handleTemplateSelect = (templateId: string) => {
    // 查找将要应用的模板
    const itemToApply = templates.find((t) => t.id === templateId);
    if (!itemToApply) return; // 如果找不到模板，则不执行任何操作

    // 如果当前内容不为空，或者当前选择的模板不是即将应用的模板并且即将应用的内容与当前内容不同时，才显示提示框
    if (
      content.trim() !== '' &&
      selectedTemplate !== templateId &&
      content !== itemToApply.content
    ) {
      Modal.confirm({
        title: t('confirmOperationTitle', { defaultValue: '确认操作' }),
        content: t('confirmOverwriteContent', {
          defaultValue: '此操作会覆盖当前编辑内容，是否继续？',
        }),
        okText: t('continue', { defaultValue: '继续' }),
        cancelText: t('cancel', { defaultValue: '取消' }),
        onOk: () => {
          setSelectedTemplate(templateId);
          setContent(itemToApply.content); // 用户确认后，覆盖内容
        },
        onCancel: () => {
          // 用户取消，不执行任何操作
          // console.log('取消应用模板');
        },
      });
    } else {
      // 如果当前内容为空，或者选择的是同一个模板且内容未变，或者即将应用的内容与当前内容相同，则直接应用模板，不提示
      setSelectedTemplate(templateId);
      setContent(itemToApply.content);
    }
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
          const newSelectedTemplate = updatedTemplates[0];
          setSelectedTemplate(newSelectedTemplate.id);
          setContent(newSelectedTemplate.content);
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

  const getContextContent = (
    cursorPos: number,
    currentDocumentContent: string,
    maxLength: number = 4000,
  ) => {
    const beforeCursor = currentDocumentContent.substring(0, cursorPos);
    const afterCursor = currentDocumentContent.substring(cursorPos);
    const insertMarker = '';
    const availableLength = maxLength - insertMarker.length;

    if (currentDocumentContent.length <= availableLength) {
      return {
        contextContent: beforeCursor + insertMarker + afterCursor,
      };
    }

    const halfLength = Math.floor(availableLength / 2);
    let finalBefore = beforeCursor;
    let finalAfter = afterCursor;

    if (beforeCursor.length > halfLength) {
      finalBefore =
        '...' + beforeCursor.substring(beforeCursor.length - halfLength + 3);
    }

    if (afterCursor.length > halfLength) {
      finalAfter = afterCursor.substring(0, halfLength - 3) + '...';
    }

    return {
      contextContent: finalBefore + insertMarker + finalAfter,
    };
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

      // 删除必须选择知识库的限制

      if (isStreaming) {
        stopOutputMessage();
        setIsStreaming(false);
        setIsAiLoading(false);
        const contentToCleanOnInterrupt =
          contentBeforeAiInsertionRef.current +
          currentStreamedAiOutput +
          contentAfterAiInsertionRef.current;
        const cleanedContent = contentToCleanOnInterrupt.replace(
          /<think>.*?<\/think>/gs,
          '',
        );
        setContent(cleanedContent);
        setCurrentStreamedAiOutput('');
        contentBeforeAiInsertionRef.current = '';
        contentAfterAiInsertionRef.current = '';
        aiInsertionStartPosRef.current = null;
        message.info('已中断上一次AI回答，正在处理新问题...');
        await new Promise((resolve) => {
          setTimeout(resolve, 100);
        });
      }

      if (cursorPosition === null) {
        message.warning('请先点击文本框以设置AI内容插入位置。');
        return;
      }

      const currentCursorPos = cursorPosition;
      contentBeforeAiInsertionRef.current = content.substring(
        0,
        currentCursorPos,
      );
      contentAfterAiInsertionRef.current = content.substring(currentCursorPos);
      aiInsertionStartPosRef.current = currentCursorPos;

      setIsAiLoading(true);
      setIsStreaming(true);
      setCurrentStreamedAiOutput('');

      try {
        const authorization = localStorage.getItem('Authorization');
        if (!authorization) {
          message.error(t('loginRequiredError'));
          setIsAiLoading(false);
          setIsStreaming(false);
          setCurrentStreamedAiOutput('');
          contentBeforeAiInsertionRef.current = '';
          contentAfterAiInsertionRef.current = '';
          aiInsertionStartPosRef.current = null;
          return;
        }

        let questionWithContext = aiQuestion;
        if (aiInsertionStartPosRef.current !== null) {
          const { contextContent } = getContextContent(
            aiInsertionStartPosRef.current,
            content,
          );
          questionWithContext = `${aiQuestion}\n\n上下文内容：\n${contextContent}`;
        }

        // 构建请求参数，只有当用户选择了知识库时才包含 kb_ids
        const requestParams: any = {
          question: questionWithContext,
          dialog_id: dialogId,
          similarity_threshold: similarityThreshold,
          keyword_similarity_weight: keywordSimilarityWeight,
          temperature: modelTemperature,
        };
        
        // 只有当用户选择了知识库时才添加 kb_ids 参数
        if (selectedKnowledgeBases.length > 0) {
          requestParams.kb_ids = selectedKnowledgeBases;
        }
        
        await sendMessage(requestParams);

        setAiQuestion('');
        if (textAreaRef.current?.resizableTextArea?.textArea) {
          textAreaRef.current.resizableTextArea.textArea.focus();
        }
      } catch (error: any) {
        console.error('AI助手处理失败:', error);
        const errorMessage =
          error.code === 'ECONNABORTED' || error.name === 'AbortError'
            ? t('aiRequestTimeoutError')
            : error.response?.data?.message
              ? `${t('aiRequestFailedError')}: ${error.response.data.message}`
              : t('aiRequestFailedError');
        message.error(errorMessage);
      }
    }
  };

  const handleSave = async () => {
    const selectedTemplateItem = templates.find(
      (item) => item.id === selectedTemplate,
    );
    const baseName = selectedTemplateItem
      ? selectedTemplateItem.name
      : t('document', { defaultValue: '文档' });
    const today = new Date();
    const dateStr = `${today.getFullYear()}${String(
      today.getMonth() + 1,
    ).padStart(2, '0')}${String(today.getDate()).padStart(2, '0')}`;
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

      // 辅助函数，用于获取图片尺寸以保持宽高比
      const getImageDimensions = (
        buffer: ArrayBuffer,
      ): Promise<{ width: number; height: number }> => {
        return new Promise((resolve, reject) => {
          const blob = new Blob([buffer]);
          const url = URL.createObjectURL(blob);
          const img = new window.Image();
          img.onload = () => {
            resolve({ width: img.naturalWidth, height: img.naturalHeight });
            URL.revokeObjectURL(url); // 清理
          };
          img.onerror = (err) => {
            reject(err);
            URL.revokeObjectURL(url); // 清理
          };
          img.src = url;
        });
      };

      // 辅助函数：解析文本类型的内联元素
      function parseTokensToRuns(
        inlineTokens: Tokens.Generic[] | undefined,
      ): TextRun[] {
        const runs: TextRun[] = [];
        if (!inlineTokens) return runs;

        inlineTokens.forEach((token) => {
          // 跳过 image token，因为它会在主循环中被特殊处理
          if (token.type === 'image') return;

          if (token.type === 'text') {
            runs.push(new TextRun(token.raw));
          } else if (token.type === 'strong' && 'text' in token) {
            runs.push(new TextRun({ text: token.text as string, bold: true }));
          } else if (token.type === 'em' && 'text' in token) {
            runs.push(
              new TextRun({ text: token.text as string, italics: true }),
            );
          } else if (token.type === 'codespan' && 'text' in token) {
            runs.push(
              new TextRun({ text: token.text as string, style: 'Consolas' }),
            );
          } else if (token.type === 'del' && 'text' in token) {
            runs.push(
              new TextRun({ text: token.text as string, strike: true }),
            );
          } else if (
            token.type === 'link' &&
            'text' in token &&
            'href' in token
          ) {
            runs.push(
              new TextRun({ text: token.text as string, style: 'Hyperlink' }),
            );
          } else if ('raw' in token) {
            runs.push(new TextRun(token.raw));
          }
        });
        return runs;
      }

      // 用于匹配 Markdown 图片语法的正则表达式
      const imageMarkdownRegex = /!\[.*?\]\((.*?)\)/;

      // 使用 for...of 循环以支持 await
      for (const token of tokens) {
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
              children: parseTokensToRuns(headingToken.tokens),
              heading: docxHeadingLevel,
              spacing: {
                after: 200 - headingToken.depth * 20,
                before: headingToken.depth === 1 ? 0 : 100,
              },
            }),
          );
        } else if (token.type === 'paragraph') {
          const paraToken = token as MarkedParagraphToken;
          const paragraphChildren: (TextRun | ImageRun)[] = [];

          if (paraToken.tokens) {
            for (const inlineToken of paraToken.tokens) {
              let isImage = false;
              let imageUrl = '';
              let rawMarkdownForImage = inlineToken.raw;

              // 方案一: `marked` 正确解析为 'image' 类型
              if (inlineToken.type === 'image') {
                isImage = true;
                imageUrl = (inlineToken as MarkedImageToken).href;
              }
              // 方案二 (后备): `marked` 未能解析，但文本内容匹配图片格式
              else if (inlineToken.type === 'text') {
                const match = inlineToken.raw.match(imageMarkdownRegex);
                if (match && match[1]) {
                  isImage = true;
                  imageUrl = match[1]; // 获取括号内的 URL
                }
              }

              // 如果是图片，则下载并处理
              if (isImage) {
                try {
                  message.info(`正在下载图片: ${imageUrl.substring(0, 50)}...`);
                  const response = await fetch(imageUrl);
                  if (!response.ok)
                    throw new Error(`下载图片失败: ${response.statusText}`);

                  const imageBuffer = await response.arrayBuffer();
                  const { width: naturalWidth, height: naturalHeight } =
                    await getImageDimensions(imageBuffer);

                  const aspectRatio =
                    naturalWidth > 0 ? naturalHeight / naturalWidth : 1;
                  const docxWidth = 540;
                  const docxHeight = docxWidth * aspectRatio;

                  paragraphChildren.push(
                    new ImageRun({
                      data: imageBuffer,
                      type: 'png',
                      transformation: {
                        width: docxWidth,
                        height: docxHeight,
                      },
                    }),
                  );
                } catch (error) {
                  console.error(`无法加载或插入图片 ${imageUrl}:`, error);
                  message.warning(
                    `图片加载失败: ${imageUrl}，已在文档中标注。`,
                  );
                  paragraphChildren.push(
                    new TextRun({
                      text: `[图片加载失败: ${rawMarkdownForImage}]`,
                      italics: true,
                      color: 'FF0000',
                    }),
                  );
                }
              } else {
                // 如果不是图片，则作为普通文本处理
                const runs = parseTokensToRuns([inlineToken]);
                paragraphChildren.push(...runs);
              }
            }
          }

          if (paragraphChildren.length > 0) {
            paragraphs.push(
              new Paragraph({
                children: paragraphChildren,
                spacing: { after: 120 },
                alignment:
                  paragraphChildren.length === 1 &&
                  paragraphChildren[0] instanceof ImageRun
                    ? AlignmentType.CENTER
                    : AlignmentType.LEFT,
              }),
            );
          } else {
            paragraphs.push(new Paragraph({}));
          }
        } else if (token.type === 'list') {
          const listToken = token as MarkedListToken;
          listToken.items.forEach((listItem: MarkedListItem) => {
            // 注意：列表项内部也可能包含图片，但为简化，此处暂不处理。
            // 如果列表项中也需要图片，需要将 paragraph 的逻辑应用到这里。
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
          paragraphs.push(new Paragraph({}));
        }
      }

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

  // 插入图片按钮点击
  const handleInsertImage = () => {
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
      fileInputRef.current.click();
    }
  };

  // 图片上传并插入markdown
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    // 校验图片类型
    if (!file.type.startsWith('image/')) {
      message.error(
        t('onlyImageAllowed', { defaultValue: '只能上传图片文件' }),
      );
      return;
    }
    try {
      const url = await uploadImage(file);
      // 插入markdown
      let insertText = `![图片](${url})`;
      let insertPos = cursorPosition ?? content.length;
      const before = content.slice(0, insertPos);
      const after = content.slice(insertPos);
      const newContent = before + insertText + after;
      setContent(newContent);
      // 设置光标到图片后
      setCursorPosition(insertPos + insertText.length);
      setShowCursorIndicator(true);
      // 聚焦到编辑器
      setTimeout(() => {
        if (textAreaRef.current?.resizableTextArea?.textArea) {
          textAreaRef.current.resizableTextArea.textArea.focus();
          textAreaRef.current.resizableTextArea.textArea.selectionStart =
            insertPos + insertText.length;
          textAreaRef.current.resizableTextArea.textArea.selectionEnd =
            insertPos + insertText.length;
        }
      }, 0);
    } catch (err) {
      message.error(t('imageUploadFailed', { defaultValue: '图片上传失败' }));
    }
  };

  // 添加表格转换函数
  const convertTableToMarkdown = (tableHtml: string): string => {
    const parser = new DOMParser();
    const doc = parser.parseFromString(tableHtml, 'text/html');
    const table = doc.querySelector('table');

    if (!table) return tableHtml;

    const rows = Array.from(table.querySelectorAll('tr'));
    if (rows.length === 0) return tableHtml;

    let markdown = '';

    rows.forEach((row, rowIndex) => {
      const cells = Array.from(row.querySelectorAll('td, th'));
      const cellTexts = cells.map((cell) => cell.textContent?.trim() || '');

      // 添加表格行
      markdown += '| ' + cellTexts.join(' | ') + ' |\n';

      // 如果是第一行，添加分隔符
      if (rowIndex === 0) {
        markdown += '| ' + cellTexts.map(() => '---').join(' | ') + ' |\n';
      }
    });

    return markdown;
  };

  // 添加公式转换函数
  const convertFormulaToMarkdown = (
    htmlData: string,
  ): { hasFormula: boolean; text: string } => {
    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlData, 'text/html');

    // 检查是否包含MathML元素
    const mathElements = doc.querySelectorAll(
      'math, annotation, mrow, mi, mo, mn, msup, msub, mfrac',
    );
    if (mathElements.length === 0) {
      return { hasFormula: false, text: '' };
    }

    // 尝试提取公式文本
    let formulaText = '';

    // 尝试从annotation标签获取LaTeX
    const annotation = doc.querySelector(
      'annotation[encoding="application/x-tex"], annotation[encoding="LaTeX"]',
    );
    if (annotation && annotation.textContent) {
      formulaText = annotation.textContent.trim();
      return { hasFormula: true, text: `$${formulaText}$` };
    }

    // 如果没有找到LaTeX注释，尝试从MathML元素中提取文本
    const mathElement = doc.querySelector('math');
    if (mathElement) {
      formulaText = mathElement.textContent?.trim() || '';

      // 简单处理一些常见的数学符号
      formulaText = formulaText
        .replace(/\s+/g, ' ')
        .replace(/(\d+)\/(\d+)/g, '\\frac{$1}{$2}')
        .replace(/\^(\w+)/g, '^{$1}')
        .replace(/_(\w+)/g, '_{$1}');

      return { hasFormula: true, text: `$${formulaText}$` };
    }

    // 如果是行内公式，使用单个$，如果是块级公式，使用$$
    const isBlockFormula =
      htmlData.includes('\\displaystyle') ||
      htmlData.includes('\\begin{align}') ||
      htmlData.includes('\\begin{equation}');

    if (isBlockFormula) {
      return { hasFormula: true, text: `$$${formulaText}$$` };
    }

    return { hasFormula: true, text: `$${formulaText}$` };
  };

  // 添加普通文本数学公式转换函数
  const convertPlainTextFormulaToLaTeX = (text: string): string => {
    if (!text) return text;

    // 检查是否已经是LaTeX格式
    if (text.includes('\\') && /\\[a-zA-Z]+/.test(text)) {
      // 如果已经是LaTeX格式，只需添加分隔符
      return text.startsWith('$') ? text : `$${text}$`;
    }

    // 处理上标和下标
    let result = text
      // 先处理帽子符号，如 A ̂ 转换为 \hat{A}
      .replace(/([A-Za-z])\s*̂/g, '\\hat{$1}')
      // 处理波浪号符号，如 D ̃ 转换为 \tilde{D}
      .replace(/([A-Za-z])\s*̃/g, '\\tilde{$1}')
      // 处理上标，如 H^((3)) 转换为 H^{(3)}，然后再处理为 H^{3}
      .replace(/\^[ ]*\(\(([^)]+)\)\)/g, '^{($1)}')
      .replace(/\^[ ]*\(([^)]+)\)/g, '^{$1}')
      // 处理下标，如 H_((3)) 转换为 H_{3}
      .replace(/_[ ]*\(\(([^)]+)\)\)/g, '_{($1)}')
      .replace(/_[ ]*\(([^)]+)\)/g, '_{$1}')
      // 处理简单上标，如 H^3 转换为 H^{3}
      .replace(/\^([a-zA-Z0-9]+)/g, '^{$1}')
      // 处理简单下标，如 H_3 转换为 H_{3}
      .replace(/_([a-zA-Z0-9]+)/g, '_{$1}')
      // 处理分数，如 -1/2 转换为 -\frac{1}{2}
      .replace(/(-?\d+)\/(\d+)/g, '\\frac{$1}{$2}')
      // 处理一般分数，如 a/b 转换为 \frac{a}{b}
      .replace(/(\w+)\/(\w+)/g, '\\frac{$1}{$2}')
      // 处理希腊字母
      .replace(/φ/g, '\\phi')
      .replace(/σ/g, '\\sigma')
      .replace(/α/g, '\\alpha')
      .replace(/β/g, '\\beta')
      .replace(/γ/g, '\\gamma')
      .replace(/δ/g, '\\delta')
      .replace(/ε/g, '\\epsilon')
      .replace(/θ/g, '\\theta')
      .replace(/λ/g, '\\lambda')
      .replace(/μ/g, '\\mu')
      .replace(/π/g, '\\pi')
      .replace(/ρ/g, '\\rho')
      .replace(/τ/g, '\\tau')
      .replace(/ω/g, '\\omega')
      .replace(/Γ/g, '\\Gamma')
      .replace(/Δ/g, '\\Delta')
      .replace(/Θ/g, '\\Theta')
      .replace(/Λ/g, '\\Lambda')
      .replace(/Σ/g, '\\Sigma')
      .replace(/Φ/g, '\\Phi')
      .replace(/Ψ/g, '\\Psi')
      .replace(/Ω/g, '\\Omega')
      // 处理特殊符号
      .replace(/×/g, '\\times')
      .replace(/÷/g, '\\div')
      .replace(/±/g, '\\pm')
      .replace(/∞/g, '\\infty')
      .replace(/≤/g, '\\leq')
      .replace(/≥/g, '\\geq')
      .replace(/≠/g, '\\neq')
      .replace(/≈/g, '\\approx')
      .replace(/∑/g, '\\sum')
      .replace(/∏/g, '\\prod')
      .replace(/∫/g, '\\int')
      .replace(/∂/g, '\\partial')
      .replace(/√/g, '\\sqrt')
      .replace(/⋅/g, '\\cdot')
      // 处理乘法符号，如 αH 转换为 \alpha H
      .replace(/([\\][a-zA-Z]+)([A-Z])/g, '$1 $2')
      // 处理连续的字母变量，如 αH 转换为 \alpha H
      .replace(/([α-ωΑ-Ω])([A-Z])/g, (match, greek, letter) => {
        const greekMap: { [key: string]: string } = {
          α: '\\alpha',
          β: '\\beta',
          γ: '\\gamma',
          δ: '\\delta',
          ε: '\\epsilon',
          θ: '\\theta',
          λ: '\\lambda',
          μ: '\\mu',
          π: '\\pi',
          ρ: '\\rho',
          σ: '\\sigma',
          τ: '\\tau',
          φ: '\\phi',
          ω: '\\omega',
          Γ: '\\Gamma',
          Δ: '\\Delta',
          Θ: '\\Theta',
          Λ: '\\Lambda',
          Σ: '\\Sigma',
          Φ: '\\Phi',
          Ψ: '\\Psi',
          Ω: '\\Omega',
        };
        return (greekMap[greek] || greek) + ' ' + letter;
      });

    // 检查括号是否平衡，如果不平衡则补充
    const openParens = (result.match(/\(/g) || []).length;
    const closeParens = (result.match(/\)/g) || []).length;
    if (openParens > closeParens) {
      result += ')'.repeat(openParens - closeParens);
    }

    // 如果公式比较复杂（包含多个数学符号或特殊字符），使用块级公式
    const isComplexFormula =
      (result.match(/\\/g) || []).length > 2 ||
      result.includes('\\frac') ||
      result.includes('\\sum') ||
      result.includes('\\int') ||
      result.length > 50;

    return isComplexFormula ? `$$${result}$$` : `$${result}$`;
  };

  // 添加粘贴事件处理
  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      const clipboardData = e.clipboardData;
      const htmlData = clipboardData.getData('text/html');
      const textData = clipboardData.getData('text/plain');

      // 检查是否包含表格
      if (htmlData && htmlData.includes('<table')) {
        e.preventDefault();

        // 转换表格为Markdown
        const markdownTable = convertTableToMarkdown(htmlData);

        // 获取当前光标位置
        const textarea = textAreaRef.current?.resizableTextArea?.textArea;
        if (textarea) {
          const start = textarea.selectionStart;
          const end = textarea.selectionEnd;
          const currentContent = content;

          // 插入转换后的Markdown表格
          const newContent =
            currentContent.substring(0, start) +
            markdownTable +
            currentContent.substring(end);

          setContent(newContent);

          // 设置新的光标位置
          setTimeout(() => {
            const newPosition = start + markdownTable.length;
            textarea.setSelectionRange(newPosition, newPosition);
          }, 0);
        }
        return;
      }

      // 检查是否包含MathML格式的数学公式
      if (htmlData && htmlData.includes('<math')) {
        const { hasFormula, text } = convertFormulaToMarkdown(htmlData);
        if (hasFormula && text) {
          e.preventDefault();

          // 获取当前光标位置
          const textarea = textAreaRef.current?.resizableTextArea?.textArea;
          if (textarea) {
            const start = textarea.selectionStart;
            const end = textarea.selectionEnd;
            const currentContent = content;

            // 插入转换后的Markdown公式
            const newContent =
              currentContent.substring(0, start) +
              text +
              currentContent.substring(end);

            setContent(newContent);

            // 设置新的光标位置
            setTimeout(() => {
              const newPosition = start + text.length;
              textarea.setSelectionRange(newPosition, newPosition);
            }, 0);
          }
          return;
        }
      }

      // 检查是否是普通文本格式的数学公式
      if (textData) {
        // 检测是否可能是数学公式（包含特殊字符、上下标等）
        const hasMathSymbols =
          /[φσαβγδεθλμπρτω∑∏∫∂√⋅×÷±∞≤≥≠≈^_(){}[\]]/i.test(textData) ||
          /\^|\(|\)|\[|\]|\{|\}|_|\/|\^|[A-Z]\d/.test(textData);

        if (hasMathSymbols && textData.length < 200) {
          // 限制长度，避免处理大段文本
          // 尝试转换为LaTeX格式
          const latexFormula = convertPlainTextFormulaToLaTeX(textData);

          // 如果转换后的公式与原文本不同，则认为是有效的转换
          if (latexFormula !== textData && latexFormula !== `$${textData}$`) {
            e.preventDefault();

            // 获取当前光标位置
            const textarea = textAreaRef.current?.resizableTextArea?.textArea;
            if (textarea) {
              const start = textarea.selectionStart;
              const end = textarea.selectionEnd;
              const currentContent = content;

              // 插入转换后的LaTeX公式
              const newContent =
                currentContent.substring(0, start) +
                latexFormula +
                currentContent.substring(end);

              setContent(newContent);

              // 设置新的光标位置
              setTimeout(() => {
                const newPosition = start + latexFormula.length;
                textarea.setSelectionRange(newPosition, newPosition);
              }, 0);
            }
            return;
          }
        }

        // 检查是否是从Word复制的LaTeX公式
        if (textData.includes('\\') || textData.match(/\$.*\$/)) {
          // 尝试检测是否是LaTeX格式
          const isLatex =
            /\\[a-zA-Z]+/.test(textData) ||
            textData.includes('\\frac') ||
            textData.includes('\\sum') ||
            textData.includes('\\int');

          if (isLatex) {
            e.preventDefault();

            // 如果文本已经被$包围，则直接使用
            let formulaText = textData;
            if (!textData.startsWith('$') && !textData.endsWith('$')) {
              // 判断是否应该是块级公式
              const isBlockFormula =
                textData.includes('\\displaystyle') ||
                textData.includes('\\begin{align}') ||
                textData.includes('\\begin{equation}');

              formulaText = isBlockFormula
                ? `$$${textData}$$`
                : `$${textData}$`;
            }

            // 获取当前光标位置
            const textarea = textAreaRef.current?.resizableTextArea?.textArea;
            if (textarea) {
              const start = textarea.selectionStart;
              const end = textarea.selectionEnd;
              const currentContent = content;

              // 插入LaTeX公式
              const newContent =
                currentContent.substring(0, start) +
                formulaText +
                currentContent.substring(end);

              setContent(newContent);

              // 设置新的光标位置
              setTimeout(() => {
                const newPosition = start + formulaText.length;
                textarea.setSelectionRange(newPosition, newPosition);
              }, 0);
            }
          }
        }
      }
    },
    [content],
  );

  const renderEditor = () => {
    let displayContent = content; // 默认显示主内容状态

    // 如果 AI 正在流式输出，则动态拼接显示内容
    if (isStreaming && aiInsertionStartPosRef.current !== null) {
      // 实时显示时，保留 <think> 标签内容
      displayContent =
        contentBeforeAiInsertionRef.current +
        currentStreamedAiOutput +
        contentAfterAiInsertionRef.current;
    } else if (showCursorIndicator && cursorPosition !== null) {
      // 如果不处于流式输出中，但设置了光标，则显示插入标记
      // (由于 INSERTION_MARKER 为空字符串，这一步实际上不会添加可见标记)
      const beforeCursor = content.substring(0, cursorPosition);
      const afterCursor = content.substring(cursorPosition);
      displayContent = beforeCursor + INSERTION_MARKER + afterCursor;
    }

    return (
      <div style={{ position: 'relative', height: '100%', width: '100%' }}>
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
          value={displayContent} // 使用动态的 displayContent
          onChange={(e) => {
            const currentInputValue = e.target.value; // 获取当前输入框中的完整内容
            const newCursorSelectionStart = e.target.selectionStart;
            let finalContent = currentInputValue;
            let finalCursorPosition = newCursorSelectionStart;

            // 如果用户在 AI 流式输出时输入，则中断 AI 输出，并“固化”当前内容（清除 <think> 标签）
            if (isStreaming) {
              stopOutputMessage(); // 中断 SSE 连接
              setIsStreaming(false); // 停止流式输出
              setIsAiLoading(false); // 停止加载状态

              // 此时 currentInputValue 已经包含了所有已流出的 AI 内容 (包括 <think> 标签)
              // 移除 <think> 标签
              const contentWithoutThinkTags = currentInputValue.replace(
                /<think>.*?<\/think>/gs,
                '',
              );
              finalContent = contentWithoutThinkTags;

              // 重新计算光标位置，因为内容长度可能因移除 <think> 标签而改变
              const originalLength = currentInputValue.length;
              const cleanedLength = finalContent.length;

              // 假设光标是在 AI 插入点之后，或者在用户输入后新位置，需要调整
              // 如果光标在被移除的 <think> 区域内部，或者在移除区域之后，需要回退相应长度
              if (
                newCursorSelectionStart > (aiInsertionStartPosRef.current || 0)
              ) {
                // 假设 aiInsertionStartPosRef.current 是 AI 内容的起始点
                finalCursorPosition =
                  newCursorSelectionStart - (originalLength - cleanedLength);
                // 确保光标不会超出新内容的末尾
                if (finalCursorPosition > cleanedLength) {
                  finalCursorPosition = cleanedLength;
                }
              } else {
                finalCursorPosition = newCursorSelectionStart; // 光标在 AI 插入点之前，无需调整
              }

              // 清理流式相关的临时状态和 useRef
              setCurrentStreamedAiOutput('');
              contentBeforeAiInsertionRef.current = '';
              contentAfterAiInsertionRef.current = '';
              aiInsertionStartPosRef.current = null;
            }

            // 检查内容中是否包含 INSERTION_MARKER，如果包含则移除
            // 由于 INSERTION_MARKER 为空字符串，此逻辑块影响很小
            const markerIndex = finalContent.indexOf(INSERTION_MARKER); // 对已处理的 finalContent 进行检查
            if (markerIndex !== -1) {
              const contentWithoutMarker = finalContent.replace(
                INSERTION_MARKER,
                '',
              );
              finalContent = contentWithoutMarker;
              if (newCursorSelectionStart > markerIndex) {
                // 此处的 newCursorSelectionStart 仍然是原始的，需要与 markerIndex 比较
                finalCursorPosition =
                  finalCursorPosition - INSERTION_MARKER.length;
              }
            }

            setContent(finalContent); // 更新主内容状态
            setCursorPosition(finalCursorPosition); // 更新光标位置状态
            // 手动设置光标位置
            setShowCursorIndicator(true); // 用户输入时，表明已设置光标位置，持续显示标记
          }}
          onClick={(e) => {
            const target = e.target as HTMLTextAreaElement;
            setCursorPosition(target.selectionStart);
            setShowCursorIndicator(true); // 点击时设置光标位置并显示标记
            target.focus(); // 确保点击后立即聚焦
          }}
          onKeyUp={(e) => {
            const target = e.target as HTMLTextAreaElement;
            setCursorPosition(target.selectionStart);
            setShowCursorIndicator(true); // 键盘抬起时设置光标位置并显示标记
          }}
          onPaste={handlePaste}
          placeholder={t('writePlaceholder')}
          autoSize={false}
        />
      </div>
    );
  };

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
        {/* 预览模式下，通常不显示 <think> 标签，所以这里不需要特殊处理 */}
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

  // ... JSX 结构无变化，保持原样
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
                    item.isCustom && ( // 只对自定义模板显示删除按钮
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
                      </Popconfirm>
                    ),
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
              {/* 插入图片按钮移到预览按钮右侧，导出按钮左侧 */}
              <Button icon={<UploadOutlined />} onClick={handleInsertImage}>
                {t('insertImage', { defaultValue: '插入图片' })}
              </Button>
              <Button type="primary" onClick={handleSave}>
                {t('saveToWord', { defaultValue: '导出为Word' })}
              </Button>
              {/* 隐藏的文件选择框 */}
              <input
                type="file"
                accept="image/*"
                ref={fileInputRef}
                style={{ display: 'none' }}
                onChange={handleFileChange}
              />
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
            <Input.TextArea
              placeholder={t('askAI')}
              autoSize={{ minRows: 2, maxRows: 5 }}
              value={aiQuestion}
              onChange={(e) => setAiQuestion(e.target.value)}
              onKeyDown={handleAiQuestionSubmit}
              disabled={isAiLoading}
            />
            {isStreaming ? (
              <div
                style={{
                  fontSize: '12px',
                  color: '#faad14',
                  padding: '6px 10px',
                  backgroundColor: '#fffbe6',
                  borderRadius: '4px',
                  border: '1px solid #ffe58f',
                }}
              >
                ✨ AI正在生成回答，请稍候...
              </div>
            ) : cursorPosition !== null ? (
              <div
                style={{
                  fontSize: '12px',
                  color: '#666',
                  padding: '6px 10px',
                  backgroundColor: '#e6f7ff',
                  borderRadius: '4px',
                  border: '1px solid #91d5ff',
                }}
              >
                💡 AI回答将插入到文档光标位置 (第 {cursorPosition} 个字符)。
              </div>
            ) : (
              <div
                style={{
                  fontSize: '12px',
                  color: '#f5222d',
                  padding: '6px 10px',
                  backgroundColor: '#fff1f0',
                  borderRadius: '4px',
                  border: '1px solid #ffccc7',
                }}
              >
                👆 请在上方文档中点击，设置AI内容插入位置。
              </div>
            )}
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
