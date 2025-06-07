import { useEffect, useState } from 'react';

/**
 * 一个安全的、对服务器端渲染(SSR)友好的自定义Hook，用于管理存储在localStorage中的状态。
 * 它能防止在服务器端或构建时访问localStorage，从而避免水合错误（hydration errors）。
 *
 * @param key - localStorage中存储值的键名。
 * @param defaultValue - 当localStorage中没有值或在服务器端渲染时使用的默认值。
 * @returns 返回一个类似 `useState` 的元组 `[state, setState]`。
 */
export function useSafeLocalStorageState<T>(key: string, defaultValue: T) {
  // 1. 初始状态始终使用传入的默认值。
  // 这确保了在服务器端和客户端的首次渲染中，组件的状态是一致的。
  const [state, setState] = useState<T>(defaultValue);

  // 2. 使用useEffect，确保以下代码只在客户端（浏览器）环境执行。
  // useEffect在服务器端渲染期间不会运行。
  useEffect(() => {
    try {
      const storedValue = localStorage.getItem(key);
      // 只有当localStorage中确实存在值时，才更新状态。
      if (storedValue !== null) {
        setState(JSON.parse(storedValue) as T);
      }
    } catch (error) {
      console.error(`Error reading localStorage key "${key}":`, error);
      // 如果读取或解析JSON失败，状态将保持为defaultValue，不会导致应用崩溃。
    }
  }, [key]); // 依赖项是key，通常不会改变，所以这个effect只在组件挂载后运行一次。

  /**
   * 一个封装了setState的函数，它会同时更新React状态和localStorage。
   * @param newValue - 新的状态值，或一个接收前一个状态并返回新状态的函数。
   */
  const setAndStoreState = (newValue: T | ((prevState: T) => T)) => {
    setState((prevState) => {
      // 支持函数式更新，如 `setState(prev => prev + 1)`
      const valueToStore =
        newValue instanceof Function ? newValue(prevState) : newValue;

      try {
        // 将新状态序列化并存储到localStorage。
        localStorage.setItem(key, JSON.stringify(valueToStore));
      } catch (error) {
        console.error(`Error setting localStorage key "${key}":`, error);
      }
      return valueToStore;
    });
  };

  // 返回与useState兼容的数组/元组。
  return [state, setAndStoreState] as const;
}
