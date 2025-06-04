import { Authorization } from '@/constants/authorization';
import { IAnswer } from '@/interfaces/database/chat';
import { IKnowledge } from '@/interfaces/database/knowledge';
import kbService from '@/services/knowledge-service';
import api from '@/utils/api';
import { getAuthorization } from '@/utils/authorization-util';
import { useQuery } from '@tanstack/react-query';
import { EventSourceParserStream } from 'eventsource-parser/stream';
import { useCallback, useRef, useState } from 'react';

// 查询知识库数据
export const useFetchKnowledgeList = (
  shouldFilterListWithoutDocument: boolean = false,
): {
  list: IKnowledge[];
  loading: boolean;
} => {
  const { data, isFetching: loading } = useQuery({
    queryKey: ['fetchKnowledgeList'],
    initialData: [],
    gcTime: 0,
    queryFn: async () => {
      const { data } = await kbService.getList();
      const list = data?.data?.kbs ?? [];
      return shouldFilterListWithoutDocument
        ? list.filter((x: IKnowledge) => x.chunk_num > 0)
        : list;
    },
  });

  return { list: data, loading };
};

// 发送问答信息
export const useSendMessageWithSse = (url: string = api.writeChat) => {
  const [answer, setAnswer] = useState<IAnswer>({} as IAnswer);
  const [done, setDone] = useState(true);
  const timer = useRef<any>();
  const sseRef = useRef<AbortController>();

  const initializeSseRef = useCallback(() => {
    sseRef.current = new AbortController();
  }, []);

  const resetAnswer = useCallback(() => {
    if (timer.current) {
      clearTimeout(timer.current);
    }
    timer.current = setTimeout(() => {
      setAnswer({} as IAnswer);
      clearTimeout(timer.current);
    }, 1000);
  }, []);

  const send = useCallback(
    async (
      body: any,
      controller?: AbortController,
    ): Promise<{ response: Response; data: ResponseType } | undefined> => {
      initializeSseRef();
      try {
        setDone(false);
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            [Authorization]: getAuthorization(),
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(body),
          signal: controller?.signal || sseRef.current?.signal,
        });

        const res = response.clone().json();

        const reader = response?.body
          ?.pipeThrough(new TextDecoderStream())
          .pipeThrough(new EventSourceParserStream())
          .getReader();

        while (true) {
          const x = await reader?.read();
          if (x) {
            const { done, value } = x;
            if (done) {
              console.info('done');
              resetAnswer();
              break;
            }
            try {
              const val = JSON.parse(value?.data || '');
              const d = val?.data;
              if (typeof d !== 'boolean') {
                console.info('data:', d);
                setAnswer({
                  ...d,
                  answer: d.answer,
                  conversationId: body?.conversation_id,
                });
              }
            } catch (e) {
              console.warn(e);
            }
          }
        }
        console.info('done?');
        setDone(true);
        resetAnswer();
        return { data: await res, response };
      } catch (e) {
        setDone(true);
        resetAnswer();

        console.warn(e);
      }
    },
    [initializeSseRef, url, resetAnswer],
  );

  const stopOutputMessage = useCallback(() => {
    sseRef.current?.abort();
  }, []);

  return { send, answer, done, setDone, resetAnswer, stopOutputMessage };
};
