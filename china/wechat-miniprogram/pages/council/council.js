/**
 * MEOKCLAW 微信小程序 — 议会页面 (Council Mode)
 *
 * 功能:
 *   - 多模型议会审议
 *   - 共识度可视化
 *   - 模型异议展示
 *   - 成本透明
 *   - 审议历史
 *
 * 这是 MEOKCLAW 的核心差异化功能 — 多模型民主决策。
 */

const api = require('../../utils/api');
const app = getApp();

Page({
  data: {
    // 输入
    prompt: '',
    // 是否正在审议
    isDeliberating: false,
    // 审议进度 (0-100)
    progress: 0,
    // 当前步骤
    currentStep: '',
    // 结果
    result: null,
    // 历史记录
    history: [],
    // 模型配置
    models: [
      { id: 'deepseek-v4-flash', name: 'DeepSeek Flash', selected: true, color: '#e94560' },
      { id: 'kimi-k2.6', name: 'Kimi K2.6', selected: true, color: '#0f3460' },
      { id: 'qwen3-235b', name: 'Qwen 3', selected: true, color: '#16c79a' },
      { id: 'baidu-ernie-4.5', name: '文心 4.5', selected: false, color: '#533483' },
      { id: 'huawei-pangu-v2', name: '盘古 V2', selected: false, color: '#f9a826' },
    ],
    // 共识阈值
    consensusThreshold: 0.6,
    // 显示高级设置
    showAdvanced: false,
  },

  onLoad() {
    this.loadHistory();
  },

  // ─────────────────────────────────────────────────────────────────────────
  // 输入处理
  // ─────────────────────────────────────────────────────────────────────────

  onPromptInput(e) {
    this.setData({ prompt: e.detail.value });
  },

  onConsensusChange(e) {
    const thresholds = [0.5, 0.6, 0.7, 0.8, 0.9];
    this.setData({ consensusThreshold: thresholds[e.detail.value] });
  },

  toggleModel(e) {
    const index = e.currentTarget.dataset.index;
    const models = this.data.models.slice();
    models[index].selected = !models[index].selected;

    // 确保至少选一个
    const selectedCount = models.filter(m => m.selected).length;
    if (selectedCount === 0) {
      wx.showToast({ title: '至少选择一个模型', icon: 'none' });
      return;
    }

    this.setData({ models });
  },

  toggleAdvanced() {
    this.setData({ showAdvanced: !this.data.showAdvanced });
  },

  // ─────────────────────────────────────────────────────────────────────────
  // 议会审议
  // ─────────────────────────────────────────────────────────────────────────

  async startCouncil() {
    const prompt = this.data.prompt.trim();
    if (!prompt) {
      wx.showToast({ title: '请输入审议议题', icon: 'none' });
      return;
    }

    // 检查登录
    if (!app.globalData.isLoggedIn) {
      try {
        await app.login();
      } catch (e) {
        wx.showToast({ title: '登录失败', icon: 'none' });
        return;
      }
    }

    const selectedModels = this.data.models
      .filter(m => m.selected)
      .map(m => m.id);

    this.setData({
      isDeliberating: true,
      progress: 0,
      currentStep: '内容安全审查中...',
      result: null,
    });

    // 模拟进度动画
    const progressInterval = setInterval(() => {
      this.setData({
        progress: Math.min(this.data.progress + Math.random() * 15, 90),
      });
      if (this.data.progress > 30 && this.data.progress < 50) {
        this.setData({ currentStep: '各模型独立推理中...' });
      } else if (this.data.progress > 50 && this.data.progress < 80) {
        this.setData({ currentStep: '共识分析与比对中...' });
      }
    }, 800);

    try {
      const res = await api.sendCouncil(prompt, {
        models: selectedModels,
        consensusThreshold: this.data.consensusThreshold,
      });

      clearInterval(progressInterval);

      this.setData({
        isDeliberating: false,
        progress: 100,
        result: {
          text: res.text,
          consensusScore: res.consensus_score,
          totalCost: res.total_cost,
          totalLatencyMs: res.total_latency_ms,
          disagreeingModels: res.disagreeing_models,
          models: res.models,
          prompt: prompt,
          timestamp: Date.now(),
        },
      });

      // 保存到历史
      this.saveToHistory(this.data.result);

    } catch (e) {
      clearInterval(progressInterval);
      this.setData({
        isDeliberating: false,
        progress: 0,
      });

      if (e.message && e.message.includes('内容被拦截')) {
        // 已在 API 层处理
      } else {
        wx.showModal({
          title: '审议失败',
          content: '议会服务暂时不可用，请稍后再试。',
          showCancel: false,
        });
      }
    }
  },

  // ─────────────────────────────────────────────────────────────────────────
  // 结果展示
  // ─────────────────────────────────────────────────────────────────────────

  getConsensusColor(score) {
    if (score >= 0.8) return '#16c79a'; // 绿色 — 高度共识
    if (score >= 0.6) return '#f9a826'; // 橙色 — 基本共识
    return '#e94560'; // 红色 — 分歧较大
  },

  getConsensusLabel(score) {
    if (score >= 0.8) return '高度共识';
    if (score >= 0.6) return '基本共识';
    return '存在分歧';
  },

  // ─────────────────────────────────────────────────────────────────────────
  // 历史记录
  // ─────────────────────────────────────────────────────────────────────────

  loadHistory() {
    try {
      const history = wx.getStorageSync('meokclaw_council_history') || [];
      this.setData({ history: history.slice(0, 20) });
    } catch (e) {
      console.error('[MEOKCLAW] 加载历史失败:', e);
    }
  },

  saveToHistory(result) {
    const history = [result, ...this.data.history].slice(0, 50);
    this.setData({ history });
    wx.setStorageSync('meokclaw_council_history', history);
  },

  clearHistory() {
    wx.showModal({
      title: '确认清除',
      content: '是否清除所有议会历史记录？',
      success: (res) => {
        if (res.confirm) {
          this.setData({ history: [] });
          wx.removeStorageSync('meokclaw_council_history');
          wx.showToast({ title: '已清除', icon: 'success' });
        }
      },
    });
  },

  viewHistoryItem(e) {
    const index = e.currentTarget.dataset.index;
    const item = this.data.history[index];
    this.setData({
      prompt: item.prompt,
      result: item,
    });
  },

  // ─────────────────────────────────────────────────────────────────────────
  // 分享
  // ─────────────────────────────────────────────────────────────────────────

  onShareAppMessage() {
    return {
      title: 'MEOKCLAW 智能议会 — 多模型民主决策',
      path: '/pages/council/council',
      imageUrl: '/images/share_council.png',
    };
  },

  onShareTimeline() {
    return {
      title: 'MEOKCLAW 智能议会',
      query: '',
    };
  },
});
