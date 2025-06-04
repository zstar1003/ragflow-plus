import HightLightMarkdown from '@/components/highlight-markdown';
import { useTranslate } from '@/hooks/common-hooks';
import {
  useFetchKnowledgeList,
  useSendMessageWithSse,
} from '@/hooks/write-hooks';

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

// 定义插入点标记，以便在onChange时识别并移除
// const INSERTION_MARKER = '【AI内容将插入此处】';
const INSERTION_MARKER = ''; // 保持为空字符串，不显示实际标记

const Write = () => {
  const { t } = useTranslate('write');
  const [content, setContent] = useState('');
  const [aiQuestion, setAiQuestion] = useState('');
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [dialogId] = useState('');
  // cursorPosition 存储用户点击设定的插入点位置
  const [cursorPosition, setCursorPosition] = useState<number | null>(null);
  // showCursorIndicator 现在仅用于控制文档中是否显示 'INSERTION_MARKER'，
  // 并且一旦设置了光标位置，就希望它保持为 true，除非内容被清空或主动重置。
  const [showCursorIndicator, setShowCursorIndicator] = useState(false);
  const textAreaRef = useRef<any>(null); // Ant Design Input.TextArea 的 ref 类型

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
  const [isStreaming, setIsStreaming] = useState(false); // 标记AI是否正在流式输出

  // 新增状态和 useRef，用于流式输出管理
  // currentStreamedAiOutput 现在将直接接收 useSendMessageWithSse 返回的累积内容
  const [currentStreamedAiOutput, setCurrentStreamedAiOutput] = useState('');
  // 使用 useRef 存储 AI 插入点前后的内容，以及插入点位置，避免在流式更新中出现闭包陷阱
  const contentBeforeAiInsertionRef = useRef('');
  const contentAfterAiInsertionRef = useRef('');
  const aiInsertionStartPosRef = useRef<number | null>(null);

  // 使用 useFetchKnowledgeList hook 获取真实数据
  const { list: knowledgeList, loading: isLoadingKnowledgeList } =
    useFetchKnowledgeList(true);

  // 使用流式消息发送钩子
  const {
    send: sendMessage,
    answer,
    done,
    stopOutputMessage,
  } = useSendMessageWithSse();

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
  // 阶段1: 累积 AI 输出片段，用于实时显示（包括 <think> 标签）
  // 这个 useEffect 确保 currentStreamedAiOutput 始终是实时更新的、包含 <think> 标签的完整内容
  useEffect(() => {
    if (isStreaming && answer && answer.answer) {
      setCurrentStreamedAiOutput(answer.answer);
    }
  }, [isStreaming, answer]);

  // 阶段2: 当流式输出完成时 (done 为 true)
  // 这个 useEffect 负责在流式输出结束时执行清理和最终内容更新
  useEffect(() => {
    if (done) {
      setIsStreaming(false);
      setIsAiLoading(false);

      // --- Process the final streamed AI output before committing ---
      // 关键修改：这里**必须**使用 currentStreamedAiOutput，因为它是在流式过程中积累的、包含 <think> 标签的内容
      // answer.answer 可能在 done 阶段已经提前被钩子内部清理过，所以不能依赖它来获取带标签的原始内容。
      let processedAiOutput = currentStreamedAiOutput;
      if (processedAiOutput) {
        // Regex to remove <think>...</think> including content
        processedAiOutput = processedAiOutput.replace(
          /<think>.*?<\/think>/gs,
          '',
        );
      }
      // --- END NEW ---

      // 将最终累积的AI内容（已处理移除<think>标签）和初始文档内容拼接，更新到主内容状态
      setContent((prevContent) => {
        if (aiInsertionStartPosRef.current !== null) {
          // 使用 useRef 中存储的初始内容和最终处理过的 AI 输出
          const finalContent =
            contentBeforeAiInsertionRef.current +
            processedAiOutput +
            contentAfterAiInsertionRef.current;
          return finalContent;
        }
        return prevContent;
      });

      // AI完成回答后，将光标实际移到新内容末尾
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

      // 清理流式相关的临时状态和 useRef
      setCurrentStreamedAiOutput(''); // 清空累积内容
      contentBeforeAiInsertionRef.current = '';
      contentAfterAiInsertionRef.current = '';
      aiInsertionStartPosRef.current = null;
      setShowCursorIndicator(true);
    }
  }, [done, currentStreamedAiOutput]); // 依赖 done 和 currentStreamedAiOutput，确保在 done 时拿到最新的 currentStreamedAiOutput

  // 监听 currentStreamedAiOutput 的变化，实时更新主 content 状态以实现流式显示
  useEffect(() => {
    if (isStreaming && aiInsertionStartPosRef.current !== null) {
      // 实时更新编辑器内容，保留 <think> 标签内容
      setContent(
        contentBeforeAiInsertionRef.current +
          currentStreamedAiOutput +
          contentAfterAiInsertionRef.current,
      );
      // 同时更新 cursorPosition，让光标跟随 AI 输出移动（基于包含 think 标签的原始长度）
      setCursorPosition(
        aiInsertionStartPosRef.current + currentStreamedAiOutput.length,
      );
    }
  }, [currentStreamedAiOutput, isStreaming, aiInsertionStartPosRef]);

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
    // 防抖保存，防止频繁写入 localStorage
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

  // 删除模板
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

  // 获取上下文内容的辅助函数
  const getContextContent = (
    cursorPos: number,
    currentDocumentContent: string,
    maxLength: number = 4000,
  ) => {
    // 注意: 这里的 currentDocumentContent 传入的是 AI 提问时编辑器里的总内容，
    // 而不是 contentBeforeAiInsertionRef + contentAfterAiInsertionRef，因为可能包含标记
    const beforeCursor = currentDocumentContent.substring(0, cursorPos);
    const afterCursor = currentDocumentContent.substring(cursorPos);

    // 使用更明显的插入点标记，这个标记是给AI看的，不是给用户看的
    const insertMarker = '[AI 内容插入点]';
    const availableLength = maxLength - insertMarker.length;

    if (currentDocumentContent.length <= availableLength) {
      return {
        beforeCursor,
        afterCursor,
        contextContent: beforeCursor + insertMarker + afterCursor,
      };
    }

    const halfLength = Math.floor(availableLength / 2);
    let finalBefore = beforeCursor;
    let finalAfter = afterCursor;

    // 如果前半部分太长，截断并在前面加省略号
    if (beforeCursor.length > halfLength) {
      finalBefore =
        '...' + beforeCursor.substring(beforeCursor.length - halfLength + 3);
    }

    // 如果后半部分太长，截断并在后面加省略号
    if (afterCursor.length > halfLength) {
      finalAfter = afterCursor.substring(0, halfLength - 3) + '...';
    }

    return {
      beforeCursor,
      afterCursor,
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

      // 检查是否选择了知识库
      if (selectedKnowledgeBases.length === 0) {
        message.warning('请至少选择一个知识库');
        return;
      }

      // 如果AI正在流式输出，停止它，并处理新问题
      if (isStreaming) {
        stopOutputMessage(); // 停止当前的流式输出
        setIsStreaming(false); // 立即设置为false，中断流
        setIsAiLoading(false); // 确保加载状态也停止

        // 中断时立即清除流中的 <think> 标签，并更新主内容
        // 这里使用 currentStreamedAiOutput 作为基准来构建中断时的内容，
        // 因为它是屏幕上实际显示的，包含了 <think> 标签。
        const contentToCleanOnInterrupt =
          contentBeforeAiInsertionRef.current +
          currentStreamedAiOutput +
          contentAfterAiInsertionRef.current;
        const cleanedContent = contentToCleanOnInterrupt.replace(
          /<think>.*?<\/think>/gs,
          '',
        );
        setContent(cleanedContent);

        setCurrentStreamedAiOutput(''); // 清除旧的流式内容
        contentBeforeAiInsertionRef.current = ''; // 清理 useRef
        contentAfterAiInsertionRef.current = '';
        aiInsertionStartPosRef.current = null;
        message.info('已中断上一次AI回答，正在处理新问题...');
        // 稍作延迟，确保状态更新后再处理新问题，防止竞态条件
        await new Promise((resolve) => {
          setTimeout(resolve, 100);
        });
      }

      // 如果当前光标位置无效，提醒用户设置
      if (cursorPosition === null) {
        message.warning('请先点击文本框以设置AI内容插入位置。');
        return;
      }

      // 捕获 AI 插入点前后的静态内容，存储到 useRef
      const currentCursorPos = cursorPosition;
      // 此时的 content 应该是用户当前编辑器的实际内容，包括可能存在的INSERTION_MARKER
      // 但由于 INSERTION_MARKER 为空，所以就是当前的主 content
      contentBeforeAiInsertionRef.current = content.substring(
        0,
        currentCursorPos,
      );
      contentAfterAiInsertionRef.current = content.substring(currentCursorPos);
      aiInsertionStartPosRef.current = currentCursorPos; // 记录确切的开始插入位置

      setIsAiLoading(true);
      setIsStreaming(true); // 标记AI开始流式输出
      setCurrentStreamedAiOutput(''); // 清空历史累积内容，为新的流做准备

      try {
        const authorization = localStorage.getItem('Authorization');
        if (!authorization) {
          message.error(t('loginRequiredError'));
          setIsAiLoading(false);
          setIsStreaming(false); // 停止流式标记
          // 失败时也清理临时状态
          setCurrentStreamedAiOutput('');
          contentBeforeAiInsertionRef.current = '';
          contentAfterAiInsertionRef.current = '';
          aiInsertionStartPosRef.current = null;
          return;
        }

        // 构建请求内容，将上下文内容发送给AI
        let questionWithContext = aiQuestion;

        // 只有当用户设置了插入位置时才包含上下文
        if (aiInsertionStartPosRef.current !== null) {
          // 传递给 getContextContent 的 content 应该是当前编辑器完整的，包含marker的
          const { contextContent } = getContextContent(
            aiInsertionStartPosRef.current,
            content,
          );
          questionWithContext = `${aiQuestion}\n\n上下文内容：\n${contextContent}`;
        }

        // 发送流式请求
        await sendMessage({
          question: questionWithContext,
          kb_ids: selectedKnowledgeBases,
          dialog_id: dialogId,
          similarity_threshold: similarityThreshold,
          keyword_similarity_weight: keywordSimilarityWeight,
          temperature: modelTemperature,
        });

        setAiQuestion(''); // 清空输入框
        // 重新聚焦文本框，但不是AI问答框，而是主编辑区
        if (textAreaRef.current?.resizableTextArea?.textArea) {
          textAreaRef.current.resizableTextArea.textArea.focus();
        }
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
        // AI加载状态在 done 状态或错误处理中会更新，这里不主动设置为 false
        // 只有当 isStreaming 状态完全结束时，才彻底清除临时状态
      }
    }
  };

  // 导出为Word
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

  // 修改编辑器渲染函数，添加光标标记
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
            // 这里不能直接操作 DOM，因为是在 setState 之后，DOM 尚未更新
            // Ant Design Input.TextArea 会在 value 更新后自动处理光标位置
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
            <Input.TextArea
              placeholder={t('askAI')}
              autoSize={{ minRows: 2, maxRows: 5 }}
              value={aiQuestion}
              onChange={(e) => setAiQuestion(e.target.value)}
              onKeyDown={handleAiQuestionSubmit}
              disabled={isAiLoading}
            />

            {/* 插入位置提示 或 AI正在回答时的提示 - 现已常驻显示 */}
            {isStreaming ? ( // AI正在回答时优先显示此提示
              <div
                style={{
                  fontSize: '12px',
                  color: '#faad14', // 警告色
                  padding: '6px 10px',
                  backgroundColor: '#fffbe6',
                  borderRadius: '4px',
                  border: '1px solid #ffe58f',
                }}
              >
                ✨ AI正在生成回答，请稍候...
              </div>
            ) : // AI未回答时
            cursorPosition !== null ? ( // 如果光标已设置
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
              // 如果光标未设置
              <div
                style={{
                  fontSize: '12px',
                  color: '#f5222d', // 错误色，提醒用户
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
