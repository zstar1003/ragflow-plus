import type { NotifyItem } from "./type"

export const notifyData: NotifyItem[] = [
  {
    avatar: "https://gw.alipayobjects.com/zos/rmsportal/OKJXDXrmkNshAMvwtvhu.png",
    title: "V3 Admin Vite 런칭!",
    datetime: "2년 전",
    description: "Vue3, TypeScript, Element Plus, Pinia, Vite 등 주요 기술을 기반으로 한 무료 오픈소스 백오피스 관리 시스템 기본 솔루션"
  },
  {
    avatar: "https://gw.alipayobjects.com/zos/rmsportal/OKJXDXrmkNshAMvwtvhu.png",
    title: "V3 Admin 런칭!",
    datetime: "3년 전",
    description: "Vue3, TypeScript, Element Plus, Pinia를 기반으로 한 백오피스 관리 시스템 기본 솔루션"
  }
]

export const messageData: NotifyItem[] = [
  {
    avatar: "https://gw.alipayobjects.com/zos/rmsportal/ThXAXghbEsBCCSDihZxY.png",
    title: "트루먼 쇼에서",
    description: "다시는 당신을 볼 수 없다면, 좋은 아침, 좋은 오후, 좋은 저녁 되세요",
    datetime: "1998-06-05"
  },
  {
    avatar: "https://gw.alipayobjects.com/zos/rmsportal/ThXAXghbEsBCCSDihZxY.png",
    title: "서유기에서",
    description: "이 사랑에 기한을 두어야 한다면, 만 년이었으면 좋겠습니다",
    datetime: "1995-02-04"
  },
  {
    avatar: "https://gw.alipayobjects.com/zos/rmsportal/ThXAXghbEsBCCSDihZxY.png",
    title: "토토로에서",
    description: "마음에 선의를 품으면, 반드시 천사를 만날 수 있습니다",
    datetime: "1988-04-16"
  }
]

export const todoData: NotifyItem[] = [
  {
    title: "작업 이름",
    description: "이 친구는 게을러서 아무것도 남기지 않았습니다",
    extra: "시작 안됨",
    status: "info"
  },
  {
    title: "작업 이름",
    description: "이 친구는 게을러서 아무것도 남기지 않았습니다",
    extra: "진행 중",
    status: "primary"
  },
  {
    title: "작업 이름",
    description: "이 친구는 게을러서 아무것도 남기지 않았습니다",
    extra: "시간 초과",
    status: "danger"
  }
]
