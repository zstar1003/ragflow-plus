function openTab(evt, tabName) {
    // Hide all tab content
    var tabContents = document.getElementsByClassName("tab-content");
    for (var i = 0; i < tabContents.length; i++) {
        tabContents[i].classList.remove("active");
    }
    
    // Remove active class from all tab buttons
    var tabButtons = document.getElementsByClassName("tab-button");
    for (var i = 0; i < tabButtons.length; i++) {
        tabButtons[i].classList.remove("active");
    }
    
    // Show the current tab and add active class to the button
    document.getElementById(tabName).classList.add("active");
    evt.currentTarget.classList.add("active");
}
/**
 * @function fetchAndRenderMarkdown
 * @description 异步获取 Markdown 文件内容并使用 Marked.js 将其渲染为 HTML。
 * @param {string} markdownPath - Markdown 文件的路径。
 * @param {string} containerId - 用于显示渲染后 HTML 的容器元素的 ID。
 */
async function fetchAndRenderMarkdown(markdownPath, containerId) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Container element with id "${containerId}" not found.`);
        return;
    }

    try {
        const response = await fetch(markdownPath);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const markdownText = await response.text();
        const htmlContent = marked.parse(markdownText); // 使用 marked.parse()
        container.innerHTML = htmlContent;
    } catch (error) {
        console.error('Error fetching or rendering Markdown:', error);
        container.innerHTML = '<p style="color: red;">加载常见问题失败，请稍后重试。</p>';
    }
}

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', (event) => {
    // 默认打开第一个标签页
    const firstTabButton = document.querySelector('.tab-button');
    if (firstTabButton) {
        firstTabButton.click();
    }

    // 加载 FAQ Markdown 内容
    fetchAndRenderMarkdown('faq.md', 'faq-container');
    fetchAndRenderMarkdown('plan.md', 'dev-plan-container');
    // 初始化 AOS
    AOS.init({
        duration: 800, // 动画持续时间 (毫秒)
        once: true, // 动画是否只播放一次
        offset: 50, // 触发动画的偏移量 (像素)
    });
});
        