import os

import pandas as pd


def parse_excel_file(file_path):
    """
    범용 표 형식 파서 함수, Excel (.xlsx/.xls) 및 CSV 파일 지원
    통일된 형식의 데이터 블록 리스트 반환
    """
    blocks = []

    # 파일 확장자에 따라 읽기 방식 선택
    file_ext = os.path.splitext(file_path)[1].lower()

    try:
        if file_ext in (".xlsx", ".xls"):
            # Excel 파일 처리 (다중 시트)
            all_sheets = pd.read_excel(file_path, sheet_name=None)
            for sheet_name, df in all_sheets.items():
                blocks.extend(_process_dataframe(df, sheet_name))

        elif file_ext == ".csv":
            # CSV 파일 처리 (단일 시트)
            df = pd.read_csv(file_path)
            blocks.extend(_process_dataframe(df, "CSV"))

        else:
            raise ValueError(f"Unsupported file format: {file_ext}")

    except Exception as e:
        raise ValueError(f"파일 파싱 실패 {file_path}: {str(e)}")

    return blocks


def _process_dataframe(df, sheet_name):
    """단일 DataFrame 처리, 통일된 형식의 데이터 블록 생성"""
    df = df.ffill()
    headers = df.columns.tolist()
    blocks = []

    for _, row in df.iterrows():
        html_table = "<html><body><table><tr>{}</tr><tr>{}</tr></table></body></html>".format("".join(f"<td>{col}</td>" for col in headers), "".join(f"<td>{row[col]}</td>" for col in headers))

        block = {"type": "table", "img_path": "", "table_caption": "", "table_footnote": [], "table_body": html_table, "page_idx": 0}
        blocks.append(block)

    return blocks


if __name__ == "__main__":
    # 테스트 예시
    excel_path = "test.xlsx"
    csv_path = "test.csv"

    try:
        # Excel 파싱 테스트
        excel_blocks = parse_excel_file(excel_path)
        print(f"Excel 파싱 결과(총 {len(excel_blocks)}개):")
        print(excel_blocks[:1])  # 첫 번째 예시 출력

        # CSV 파싱 테스트
        csv_blocks = parse_excel_file(csv_path)
        print(f"\nCSV 파싱 결과(총 {len(csv_blocks)}개):")
        print(csv_blocks[:1])

    except Exception as e:
        print(f"오류: {str(e)}")
