type OptionValue = string | number

/** Select에 필요한 데이터 형식 */
interface SelectOption {
  value: OptionValue
  label: string
  disabled?: boolean
}

/** 인터페이스 응답 형식 */
type ApiData = ApiResponseData<SelectOption[]>

/** 입력 매개변수 형식, 현재는 api 함수만 전달하면 됩니다 */
interface FetchSelectProps {
  api: () => Promise<ApiData>
}

/** 드롭다운 선택기 Composable */
export function useFetchSelect(props: FetchSelectProps) {
  const { api } = props

  const loading = ref<boolean>(false)
  const options = ref<SelectOption[]>([])
  const value = ref<OptionValue>("")

  // 인터페이스를 호출하여 데이터 가져오기
  const loadData = () => {
    loading.value = true
    options.value = []
    api().then((res) => {
      options.value = res.data
    }).finally(() => {
      loading.value = false
    })
  }

  onMounted(() => {
    loadData()
  })

  return { loading, options, value }
}
