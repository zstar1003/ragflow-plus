import os
from io import BytesIO

from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod

def process_pdf_with_magic(file_content, callback=None):
    """
    使用magic_pdf处理PDF文件
    
    Args:
        file_content: PDF文件内容
        callback: 回调函数，用于更新进度
        
    Returns:
        解析后的内容列表
    """
    try:
        from magic_pdf.processor import PDFProcessor
        from magic_pdf.extractor import TextExtractor, ImageExtractor
        
        if callback:
            callback(0.1, "初始化Magic PDF解析器")
        
        # 创建临时文件
        temp_dir = os.path.join(os.getcwd(), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_pdf_path = os.path.join(temp_dir, "temp.pdf")
        with open(temp_pdf_path, "wb") as f:
            f.write(file_content)
        
        if callback:
            callback(0.2, "开始解析PDF")
        
        # 初始化处理器
        processor = PDFProcessor(temp_pdf_path)
        
        if callback:
            callback(0.3, "提取文本内容")
        
        # 提取文本
        text_extractor = TextExtractor(processor)
        text_content = text_extractor.extract()
        
        if callback:
            callback(0.5, "提取图片内容")
        
        # 提取图片
        image_extractor = ImageExtractor(processor)
        images = image_extractor.extract()
        
        if callback:
            callback(0.7, "组织解析结果")
        
        # 组织结果
        content_list = []
        
        # 添加文本内容
        for page_num, page_text in enumerate(text_content):
            content_list.append({
                "type": "text",
                "page": page_num + 1,
                "text": page_text
            })
        
        # 添加图片内容
        for i, img in enumerate(images):
            content_list.append({
                "type": "image",
                "page": img.get("page", i + 1),
                "image_path": img.get("path", ""),
                "caption": img.get("caption", "")
            })
        
        # 清理临时文件
        try:
            os.remove(temp_pdf_path)
        except:
            pass
        
        if callback:
            callback(1.0, "PDF解析完成")
        
        return content_list
        
    except ImportError:
        # 如果magic_pdf未安装，使用简单的文本提取
        if callback:
            callback(0.2, "Magic PDF未安装，使用备用方法")
        
        try:
            import PyPDF2
            
            if callback:
                callback(0.3, "使用PyPDF2提取文本")
            
            pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
            content_list = []
            
            for i, page in enumerate(pdf_reader.pages):
                if callback and i % 5 == 0:
                    progress = 0.3 + (i / len(pdf_reader.pages)) * 0.6
                    callback(progress, f"正在处理第 {i+1}/{len(pdf_reader.pages)} 页")
                
                text = page.extract_text()
                if text:
                    content_list.append({
                        "type": "text",
                        "page": i + 1,
                        "text": text
                    })
            
            if callback:
                callback(0.9, "文本提取完成")
            
            return content_list
            
        except Exception as e:
            if callback:
                callback(0.5, f"PDF解析失败: {str(e)}")
            
            # 最简单的备用方案
            return [{
                "type": "text",
                "page": 1,
                "text": "无法解析PDF文件内容"
            }]
    
    except Exception as e:
        if callback:
            callback(0.5, f"PDF解析失败: {str(e)}")
        
        # 出错时返回空列表
        return [{
            "type": "text",
            "page": 1,
            "text": f"解析失败: {str(e)}"
        }]