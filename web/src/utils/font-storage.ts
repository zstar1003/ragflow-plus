// 字体大小存储工具
export const FontStorageUtil = {
  // 获取字体大小
  getFontSize: (): number => {
    try {
      // 优先从localStorage获取
      const localStorageValue = localStorage.getItem('chatFontSize');
      if (localStorageValue && !isNaN(parseInt(localStorageValue))) {
        return parseInt(localStorageValue);
      }
    } catch (error) {
      console.warn('localStorage不可用，尝试从cookie获取');
    }

    try {
      // 从cookie获取
      const cookieValue = document.cookie
        .split('; ')
        .find((row) => row.startsWith('chatFontSize='))
        ?.split('=')[1];

      if (cookieValue && !isNaN(parseInt(cookieValue))) {
        return parseInt(cookieValue);
      }
    } catch (error) {
      console.warn('cookie也不可用');
    }

    return 18; // 默认字体大小
  },

  // 保存字体大小
  setFontSize: (size: number): void => {
    try {
      localStorage.setItem('chatFontSize', size.toString());
    } catch (error) {
      console.warn('localStorage保存失败，尝试使用cookie');
    }

    try {
      // 设置cookie，有效期30天
      const expires = new Date();
      expires.setDate(expires.getDate() + 30);
      document.cookie = `chatFontSize=${size}; expires=${expires.toUTCString()}; path=/`;
    } catch (error) {
      console.warn('cookie保存也失败');
    }
  },
};
