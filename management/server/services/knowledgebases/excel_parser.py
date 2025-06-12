import pandas as pd


def parse_excel(file_path):
    all_sheets = pd.read_excel(file_path, sheet_name=None)

    blocks = []

    for sheet_name, df in all_sheets.items():
        df = df.ffill()
        headers = df.columns.tolist()

        for _, row in df.iterrows():
            html_table = "<html><body><table><tr>{}</tr><tr>{}</tr></table></body></html>".format("".join(f"<td>{col}</td>" for col in headers), "".join(f"<td>{row[col]}</td>" for col in headers))
            block = {"type": "table", "img_path": "", "table_caption": [f"Sheet: {sheet_name}"], "table_footnote": [], "table_body": f"{html_table}", "page_idx": 0}
            blocks.append(block)

    return blocks


if __name__ == "__main__":
    file_path = "test_excel.xls"
    parse_excel_result = parse_excel(file_path)
    print(parse_excel_result)
