import type { App } from "vue"
import VXETable from "vxe-table" // https://vxetable.cn/#/start/install

// 전역 기본 매개변수
VXETable.setConfig({
  // 전역 크기
  size: "medium",
  // 전역 zIndex 시작값, 프로젝트의 z-index 스타일 값이 너무 클 때는 더 큰 값으로 설정하여 가려지는 것을 방지
  zIndex: 9999,
  // 버전 번호, 데이터 캐시 기능이 있는 경우에 사용되며, 버전 번호를 올리면 데이터 재설정에 사용 가능
  version: 0,
  // 전역 로딩 힌트 내용, null인 경우 텍스트를 표시하지 않음
  loadingText: null,
  table: {
    showHeader: true,
    showOverflow: "tooltip",
    showHeaderOverflow: "tooltip",
    autoResize: true,
    // stripe: false,
    border: "inner",
    // round: false,
    emptyText: "데이터 없음",
    rowConfig: {
      isHover: true,
      isCurrent: true,
      // 행 데이터의 고유 기본 키 필드명
      keyField: "_VXE_ID"
    },
    columnConfig: {
      resizable: false
    },
    align: "center",
    headerAlign: "center"
  },
  pager: {
    // size: "medium",
    // 매칭되는 스타일
    perfect: false,
    pageSize: 10,
    pagerCount: 7,
    pageSizes: [10, 20, 50],
    layouts: ["Total", "PrevJump", "PrevPage", "Number", "NextPage", "NextJump", "Sizes", "FullJump"]
  },
  modal: {
    minWidth: 500,
    minHeight: 400,
    lockView: true,
    mask: true,
    // duration: 3000,
    // marginSize: 20,
    dblclickZoom: false,
    showTitleOverflow: true,
    transfer: true,
    draggable: false
  }
})

export function installVxeTable(app: App) {
  // Vxe Table 컴포넌트 전체 가져오기
  app.use(VXETable)
}
