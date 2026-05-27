/**
 * MEOKCLAW 微信小程序 — 对话页面 (Chat Page)
 *
 * 功能:
 *   - 单轮/多轮对话
 *   - 语音输入（按住说话）
 *   - 内容安全实时提示
 *   - 成本透明展示
 *   - 符合中国用户习惯的交互设计
 */

const api = require('../../utils/api');
const app = getApp();

Page({
  data: {
    // 消息列表
    messages: [],
    // 输入框内容
    inputValue: '',
    // 是否正在加载
    isLoading: false,
    // 是否按住语音按钮
    isRecording: false,
    // 是否显示成本信息
    showCostInfo: true,
    // 当前使用的模型
    currentModel: 'deepseek-v4-flash',
    // 滚动到底部标识
    scrollToBottom: '',
    // 欢迎消息
    welcomeMessage: {
      id: 'welcome',
      role: 'assistant',
      content: '您好！我是 MEOKCLAW 智能助手。\n\n我可以帮您：\n• 解答问题\n• 分析决策（议会模式）\n• 内容安全审查\n\n所有数据处理均符合《个人信息保护法》。',
      timestamp: Date.now(),
      cost: 0,
    },
  },

  onLoad(options) {
    // 初始化欢迎消息
    this.setData({
      messages: [this.data.welcomeMessage],
    });

    // 检查登录状态
    if (!app.globalData.isLoggedIn) {
      this.handleLogin();
    }
  },

  onReady() {
    this.scrollToBottom();
  },

  // ─────────────────────────────────────────────────────────────────────────
  // 登录处理
  // ─────────────────────────────────────────────────────────────────────────

  async handleLogin() {
    try {
      wx.showLoading({ title: '登录中...' });
      await app.login();
      wx.hideLoading();
      wx.showToast({ title: '登录成功', icon: 'success' });
    } catch (e) {
      wx.hideLoading();
      console.error('[MEOKCLAW] 登录失败:', e);
      wx.showModal({
        title: '登录失败',
        content: '无法获取用户身份，部分功能可能受限。',
        showCancel: false,
      });
    }
  },

  // ─────────────────────────────────────────────────────────────────────────
  // 消息发送与接收
  // ─────────────────────────────────────────────────────────────────────────

  /**
   * 输入框内容变化
   */
  onInputChange(e) {
    this.setData({
      inputValue: e.detail.value,
    });
  },

  /**
   * 发送消息
   */
  async sendMessage() {
    const prompt = this.data.inputValue.trim();
    if (!prompt) return;

    // 检查登录
    if (!app.globalData.isLoggedIn) {
      await this.handleLogin();
      if (!app.globalData.isLoggedIn) return;
    }

    // 添加用户消息
    const userMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: prompt,
      timestamp: Date.now(),
    };

    this.setData({
      messages: [...this.data.messages, userMessage],
      inputValue: '',
      isLoading: true,
    });

    this.scrollToBottom();

    try {
      // 发送请求
      const res = await api.sendChat(prompt, {
        model: this.data.currentModel,
        councilMode: false, // 单轮对话不使用议会模式
      });

      // 添加助手回复
      const assistantMessage = {
        id: `assistant_${Date.now()}`,
        role: 'assistant',
        content: res.text,
        timestamp: Date.now(),
        cost: res.cost,
        model: res.model,
        latencyMs: res.latency_ms,
      };

      this.setData({
        messages: [...this.data.messages, assistantMessage],
        isLoading: false,
      });
    } catch (e) {
      console.error('[MEOKCLAW] 发送失败:', e);

      const errorMessage = {
        id: `error_${Date.now()}`,
        role: 'error',
        content: '抱歉，服务暂时不可用，请稍后再试。',
        timestamp: Date.now(),
      };

      this.setData({
        messages: [...this.data.messages, errorMessage],
        isLoading: false,
      });
    }

    this.scrollToBottom();
  },

  /**
   * 快速跳转到议会模式
   */
  goToCouncil() {
    wx.switchTab({
      url: '/pages/council/council',
    });
  },

  // ─────────────────────────────────────────────────────────────────────────
  // 语音输入
  // ─────────────────────────────────────────────────────────────────────────

  onTouchStartRecord() {
    this.setData({ isRecording: true });

    wx.startRecord({
      success: (res) => {
        this.handleVoiceFile(res.tempFilePath);
      },
      fail: (err) => {
        console.error('[MEOKCLAW] 录音失败:', err);
        wx.showToast({ title: '录音失败', icon: 'none' });
      },
      complete: () => {
        this.setData({ isRecording: false });
      },
    });
  },

  onTouchEndRecord() {
    wx.stopRecord();
  },

  async handleVoiceFile(filePath) {
    try {
      wx.showLoading({ title: '语音识别中...' });
      const res = await api.speechToText(filePath);
      wx.hideLoading();

      if (res.text) {
        this.setData({ inputValue: res.text });
        // 自动发送
        setTimeout(() => this.sendMessage(), 100);
      }
    } catch (e) {
      wx.hideLoading();
      wx.showToast({ title: '语音识别失败', icon: 'none' });
    }
  },

  // ─────────────────────────────────────────────────────────────────────────
  // UI 交互
  // ─────────────────────────────────────────────────────────────────────────

  scrollToBottom() {
    this.setData({
      scrollToBottom: `msg_${Date.now()}`,
    });
  },

  /**
   * 复制消息内容
   */
  copyMessage(e) {
    const content = e.currentTarget.dataset.content;
    wx.setClipboardData({
      data: content,
      success: () => {
        wx.showToast({ title: '已复制', icon: 'success' });
      },
    });
  },

  /**
   * 长按消息显示操作菜单
   */
  onMessageLongPress(e) {
    const content = e.currentTarget.dataset.content;
    wx.showActionSheet({
      itemList: ['复制', '分享', '内容安全审查'],
      success: (res) => {
        if (res.tapIndex === 0) {
          this.copyMessage(e);
        } else if (res.tapIndex === 2) {
          this.checkMessageSafety(content);
        }
      },
    });
  },

  /**
   * 检查单条消息的内容安全
   */
  async checkMessageSafety(text) {
    try {
      wx.showLoading({ title: '审查中...' });
      const res = await api.checkGuardrails(text);
      wx.hideLoading();

      if (res.blocked) {
        wx.showModal({
          title: '内容安全审查结果',
          content: `检测到 ${res.violations.length} 项违规:\n${res.violations.map(v => v.description).join('\n')}`,
          showCancel: false,
        });
      } else {
        wx.showToast({ title: '内容安全', icon: 'success' });
      }
    } catch (e) {
      wx.hideLoading();
      wx.showToast({ title: '检查失败', icon: 'none' });
    }
  },

  /**
   * 切换模型选择
   */
  onModelChange(e) {
    const models = ['deepseek-v4-flash', 'kimi-k2.6', 'qwen3-235b', 'baidu-ernie-4.5'];
    const index = e.detail.value;
    this.setData({
      currentModel: models[index],
    });
    wx.showToast({
      title: `已切换: ${models[index]}`,
      icon: 'none',
    });
  },

  // ─────────────────────────────────────────────────────────────────────────
  // 下拉刷新
  // ─────────────────────────────────────────────────────────────────────────

  onPullDownRefresh() {
    // 清空消息，重新加载
    this.setData({
      messages: [this.data.welcomeMessage],
    });
    wx.stopPullDownRefresh();
  },
});
