import type { AxiosResponse } from "axios"
import type { FileData, PageQuery, PageResult } from "./type"
import { request } from "@/http/axios"
import axios from "axios"

/**
 * 파일 목록 가져오기
 * @param params 조회 매개변수
 */
export function getFileListApi(params: PageQuery & { name?: string }) {
  return request<{ data: PageResult<FileData>, code: number, message: string }>({
    url: "/api/v1/files",
    method: "get",
    params
  })
}

/**
 * 파일 다운로드 - 스트림 다운로드 사용
 * @param fileId 파일 ID
 * @param onDownloadProgress 다운로드 진행률 콜백
 */
export function downloadFileApi(
  fileId: string,
  onDownloadProgress?: (progressEvent: any) => void
): Promise<AxiosResponse<Blob>> {
  console.log(`파일 다운로드 요청 시작: ${fileId}`)
  const source = axios.CancelToken.source()

  return request({
    url: `/api/v1/files/${fileId}/download`,
    method: "get",
    responseType: "blob",
    timeout: 300000,
    onDownloadProgress,
    cancelToken: source.token,
    validateStatus: (_status) => {
      // 모든 상태 코드를 허용하여 프론트엔드에서 오류를 통합적으로 처리
      return true
    }
  }).then((response: unknown) => {
    const axiosResponse = response as AxiosResponse<Blob>
    console.log(`다운로드 응답: ${axiosResponse.status}`, axiosResponse.data)
    // 응답 객체에 필요한 속성이 포함되어 있는지 확인
    if (axiosResponse.data instanceof Blob && axiosResponse.data.size > 0) {
      // 성공적인 Blob 응답인 경우 상태 코드가 200인지 확인
      if (!axiosResponse.status) axiosResponse.status = 200
      return axiosResponse
    }
    return axiosResponse
  }).catch((error: any) => {
    console.error("다운로드 요청 실패:", error)
    // 오류 정보를 통합 형식으로 변환
    if (error.response) {
      error.response.data = {
        message: error.response.data?.message || "서버 오류"
      }
    }
    return Promise.reject(error)
  }) as Promise<AxiosResponse<Blob>>
}

/**
 * 다운로드 취소
 */
export function cancelDownload() {
  if (axios.isCancel(Error)) {
    axios.CancelToken.source().cancel("사용자가 다운로드를 취소했습니다")
  }
}

/**
 * 파일 삭제
 * @param fileId 파일 ID
 */
export function deleteFileApi(fileId: string) {
  return request<{ code: number, message: string }>({
    url: `/api/v1/files/${fileId}`,
    method: "delete"
  })
}

/**
 * 파일 일괄 삭제
 * @param fileIds 파일 ID 배열
 */
export function batchDeleteFilesApi(fileIds: string[]) {
  return request<{ code: number, message: string }>({
    url: "/api/v1/files/batch",
    method: "delete",
    data: { ids: fileIds }
  })
}

/**
 * 파일 업로드
 */
export function uploadFileApi(formData: FormData) {
  return request<{
    code: number
    data: Array<{
      name: string
      size: number
      type: string
      status: string
    }>
    message: string
  }>({
    url: "/api/v1/files/upload",
    method: "post",
    data: formData,
    headers: {
      "Content-Type": "multipart/form-data"
    }
  })
}
