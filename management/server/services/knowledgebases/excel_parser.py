import os

import pandas as pd


def parse_excel_file(file_path):
    """
    通用表格解析函数，支持 Excel (.xlsx/.xls) 和 CSV 文件
    返回统一格式的数据块列表
    """
    blocks = []

    # 根据文件扩展名选择读取方式
    file_ext = os.path.splitext(file_path)[1].lower()

    try:
        if file_ext in (".xlsx", ".xls"):
            # 处理Excel文件（多sheet）
            all_sheets = pd.read_excel(file_path, sheet_name=None)
            for sheet_name, df in all_sheets.items():
                blocks.extend(_process_dataframe(df, sheet_name))

        elif file_ext == ".csv":
            # 处理CSV文件（单sheet）
            df = pd.read_csv(file_path)
            blocks.extend(_process_dataframe(df, "CSV"))

        else:
            raise ValueError(f"Unsupported file format: {file_ext}")

    except Exception as e:
        raise ValueError(f"Failed to parse file {file_path}: {str(e)}")

    return blocks


def _process_dataframe(df, sheet_name):
    """处理单个DataFrame，生成统一格式的数据块"""
    df = df.ffill()
    headers = df.columns.tolist()
    blocks = []

    for _, row in df.iterrows():
        html_table = "<html><body><table><tr>{}</tr><tr>{}</tr></table></body></html>".format("".join(f"<td>{col}</td>" for col in headers), "".join(f"<td>{row[col]}</td>" for col in headers))

        block = {"type": "table", "img_path": "", "table_caption": "", "table_footnote": [], "table_body": html_table, "page_idx": 0}
        blocks.append(block)

    return blocks


if __name__ == "__main__":
    # 测试示例
    excel_path = "test.xlsx"
    csv_path = "test.csv"

    try:
        # 测试Excel解析
        excel_blocks = parse_excel_file(excel_path)
        print(f"Excel解析结果（共{len(excel_blocks)}条）:")
        print(excel_blocks[:1])  # 打印第一条示例

        # 测试CSV解析
        csv_blocks = parse_excel_file(csv_path)
        print(f"\nCSV解析结果（共{len(csv_blocks)}条）:")
        print(csv_blocks[:1])

    except Exception as e:
        print(f"错误: {str(e)}")
