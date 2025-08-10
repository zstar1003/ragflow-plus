// 翻译服务
export class TranslationService {
  private static instance: TranslationService;

  private constructor() {}

  public static getInstance(): TranslationService {
    if (!TranslationService.instance) {
      TranslationService.instance = new TranslationService();
    }
    return TranslationService.instance;
  }

  // 初始化翻译模型（简化版本，主要使用后端API）
  async initializeModel(): Promise<void> {
    // 简化实现，主要依赖后端API
    console.log('翻译服务已初始化，将使用后端API进行翻译');
  }

  // 将中文翻译成英文
  async translateToEnglish(chineseText: string): Promise<string> {
    try {
      // 直接使用后端API进行翻译
      return await this.translateViaAPI(chineseText);
    } catch (error) {
      console.error('翻译失败:', error);
      // 翻译失败时返回原文
      return chineseText;
    }
  }

  // 通过后端API进行翻译
  private async translateViaAPI(text: string): Promise<string> {
    try {
      const response = await fetch('/v1/translate/translate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: text,
          source_lang: 'zh',
          target_lang: 'en'
        })
      });

      if (!response.ok) {
        throw new Error(`翻译API请求失败: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      
      if (data.code === 0) {
        return data.data.translated_text || text;
      } else {
        throw new Error(data.message || '翻译失败');
      }
    } catch (error) {
      console.error('后端翻译API调用失败:', error);
      return text; // 返回原文
    }
  }

  // 检测文本是否包含中文
  containsChinese(text: string): boolean {
    return /[\u4e00-\u9fff]/.test(text);
  }

  // 检查模型是否已准备就绪
  async isModelReady(): Promise<boolean> {
    try {
      const response = await fetch('/v1/translate/health', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        return false;
      }

      const data = await response.json();
      return data.code === 0 && data.data.model_loaded;
    } catch (error) {
      console.error('翻译服务健康检查失败:', error);
      return false;
    }
  }
}

// 导出单例实例
export const translationService = TranslationService.getInstance();