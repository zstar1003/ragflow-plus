import pandas as pd


def parse_excel(file_path):
    # 读取Excel文件
    df = pd.read_excel(file_path)
    # 获取表头
    headers = df.columns.tolist()
    blocks = []

    for _, row in df.iterrows():
        # 构建HTML表格
        html_table = "<html><body><table><tr>{}</tr><tr>{}</tr></table></body></html>".format("".join(f"<td>{col}</td>" for col in headers), "".join(f"<td>{row[col]}</td>" for col in headers))
        block = {"type": "table", "img_path": "", "table_caption": [], "table_footnote": [], "table_body": f"{html_table}", "page_idx": 0}

        blocks.append(block)

    return blocks


if __name__ == "__main__":
    file_path = "test_excel.xls"
    parse_excel_result = parse_excel(file_path)
    print(parse_excel_result)
