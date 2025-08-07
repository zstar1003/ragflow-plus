import chatService from '@/services/chat-service';
import { useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

export interface ITempFileInfo {
  file_id: string;
  filename: string;
  size: number;
  content_type: string;
}

export const useUploadTempFile = () => {
  const { t } = useTranslation();

  const {
    data,
    isPending: loading,
    mutateAsync,
  } = useMutation({
    mutationKey: ['uploadTempFile'],
    mutationFn: async (params: { file: File; conversationId?: string }) => {
      console.log(
        '[DEBUG] Starting temp file upload:',
        params?.file?.name || 'unknown file',
      );

      if (!params?.file) {
        throw new Error('No file provided for upload');
      }

      const formData = new FormData();
      formData.append('file', params.file);
      if (params.conversationId) {
        formData.append('conversation_id', params.conversationId);
      }

      try {
        console.log('[DEBUG] Calling chatService.uploadTempFile');
        const response = await chatService.uploadTempFile(formData);
        console.log('[DEBUG] Upload response:', response);

        // Handle the response structure from umi-request with getResponse: true
        // response is an array [response, originalResponse] when getResponse: true
        const actualResponse = Array.isArray(response) ? response[0] : response;
        const data = actualResponse?.data || actualResponse;
        console.log('[DEBUG] Parsed data:', data);

        if (data?.code === 0) {
          console.log('[DEBUG] Upload successful');
          return data.data as ITempFileInfo;
        } else {
          console.error(
            '[DEBUG] Upload failed with code:',
            data?.code,
            'message:',
            data?.message,
          );
          throw new Error(data?.message || 'Upload failed');
        }
      } catch (error: any) {
        console.error('[DEBUG] Upload error:', error);
        throw error;
      }
    },
  });

  return { data, loading, uploadTempFile: mutateAsync };
};

export const useGetTempFile = () => {
  const getTempFile = async (fileId: string) => {
    const response = await chatService.getTempFile(fileId);

    // Handle the response structure from umi-request with getResponse: true
    const data = response.data || response;

    if (data.code === 0) {
      return data.data;
    } else {
      throw new Error(data.message || 'Get file failed');
    }
  };

  return { getTempFile };
};
