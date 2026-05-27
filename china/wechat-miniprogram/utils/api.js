/**
 * MEOKCLAW 微信小程序 API 客户端
 *
 * 封装所有与 MEOKCLAW 后端及微信桥接器的通信：
 *   - 聊天请求 (chat)
 *   - 议会模式 (council)
 *   - 内容安全审查 (guardrails)
 *   - 成本报告 (cost)
 *
 * 所有请求自动携带 anonymous_id 和 session_token。
 * 包含请求重试、错误处理、内容安全预检。
 */

const app = getApp();

const API_BASE = 'http://localhost:3201';
const WECHAT_BRIDGE = `${API_BASE}/wechat`;

/**
 * 基础请求封装
 */
function request(options) {
  return new Promise((resolve, reject) => {
    const anonymousId = app.globalData.anonymousId;
    const sessionToken = app.globalData.sessionToken;

    const header = {
      'Content-Type': 'application/json',
      ...(anonymousId ? { 'X-Anonymous-ID': anonymousId } : {}),
      ...(sessionToken ? { 'X-Session-Token': sessionToken } : {}),
      ...(options.header || {}),
    };

    wx.request({
      url: options.url,
      method: options.method || 'GET',
      data: options.data,
      header: header,
      timeout: options.timeout || 60000,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else if (res.statusCode === 403) {
          // 内容被拦截
          wx.showModal({
            title: '内容安全提示',
            content: res.data.error || '内容未通过安全审查',
            showCancel: false,
          });
          reject(new Error(res.data.error || '内容被拦截'));
        } else if (res.statusCode === 401) {
          // 会话过期，重新登录
          app.login().then(() => {
            // 重试原请求
            request(options).then(resolve).catch(reject);
          }).catch(reject);
        } else {
          reject(new Error(`HTTP ${res.statusCode}: ${JSON.stringify(res.data)}`));
        }
      },
      fail: (err) => {
        console.error('[MEOKCLAW API] 请求失败:', err);
        // 检查是否需要重试
        if (options.retryCount && options.retryCount > 0) {
          setTimeout(() => {
            request({ ...options, retryCount: options.retryCount - 1 })
              .then(resolve)
              .catch(reject);
          }, 1000);
        } else {
          wx.showToast({
            title: '网络请求失败，请检查网络',
            icon: 'none',
            duration: 3000,
          });
          reject(err);
        }
      },
    });
  });
}

// ─────────────────────────────────────────────────────────────────────────
// 聊天 API
// ─────────────────────────────────────────────────────────────────────────

/**
 * 发送单轮聊天请求
 */
function sendChat(prompt, options = {}) {
  if (!app.globalData.isLoggedIn) {
    return Promise.reject(new Error('用户未登录'));
  }

  return request({
    url: `${WECHAT_BRIDGE}/chat`,
    method: 'POST',
    data: {
      openid: app.globalData.anonymousId,
      prompt: prompt,
      council_mode: options.councilMode ?? app.globalData.councilMode,
      model_count: options.modelCount || 1,
      context: {
        model: options.model || 'deepseek-v4-flash',
        ...options.context,
      },
    },
    retryCount: 1,
  });
}

/**
 * 发送议会模式请求
 */
function sendCouncil(prompt, options = {}) {
  if (!app.globalData.isLoggedIn) {
    return Promise.reject(new Error('用户未登录'));
  }

  // 显示加载中
  wx.showLoading({
    title: '议会审议中...',
    mask: true,
  });

  return request({
    url: `${WECHAT_BRIDGE}/council`,
    method: 'POST',
    data: {
      openid: app.globalData.anonymousId,
      prompt: prompt,
      models: options.models || app.globalData.defaultModels,
      consensus_threshold: options.consensusThreshold || 0.6,
    },
    timeout: 90000,
    retryCount: 0,
  }).finally(() => {
    wx.hideLoading();
  });
}

// ─────────────────────────────────────────────────────────────────────────
// 内容安全 API
// ─────────────────────────────────────────────────────────────────────────

/**
 * 内容安全预检
 * 在发送主要请求前，先检查内容合规性
 */
function checkGuardrails(text, checkType = 'all') {
  return request({
    url: `${WECHAT_BRIDGE}/guardrails/check`,
    method: 'POST',
    data: {
      text: text,
      check_type: checkType,
    },
    timeout: 10000,
  });
}

/**
 * 微信官方内容安全接口（图片/文本）
 * 作为备用检查手段
 */
function checkWechatContentSecurity(text) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: 'https://api.weixin.qq.com/wxa/msg_sec_check',
      method: 'POST',
      data: {
        content: text,
      },
      success: (res) => {
        if (res.data && res.data.errcode === 0) {
          resolve({ safe: true });
        } else {
          resolve({ safe: false, reason: res.data.errmsg });
        }
      },
      fail: reject,
    });
  });
}

// ─────────────────────────────────────────────────────────────────────────
// 其他 API
// ─────────────────────────────────────────────────────────────────────────

/**
 * 获取成本报告
 */
function getCostReport(period = 'today') {
  return request({
    url: `${API_BASE}/api/cost-savings/summary`,
    method: 'GET',
    data: { period },
  });
}

/**
 * 获取议会历史记录
 */
function getCouncilHistory() {
  return request({
    url: `${API_BASE}/api/council/history`,
    method: 'GET',
  });
}

/**
 * 语音转文字（使用微信官方接口）
 */
function speechToText(filePath) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${WECHAT_BRIDGE}/speech-to-text`,
      filePath: filePath,
      name: 'file',
      formData: {
        openid: app.globalData.anonymousId || '',
      },
      success: (res) => {
        try {
          const data = JSON.parse(res.data);
          resolve(data);
        } catch (e) {
          reject(new Error('解析响应失败'));
        }
      },
      fail: reject,
    });
  });
}

// ─────────────────────────────────────────────────────────────────────────
// 导出
// ─────────────────────────────────────────────────────────────────────────

module.exports = {
  request,
  sendChat,
  sendCouncil,
  checkGuardrails,
  checkWechatContentSecurity,
  getCostReport,
  getCouncilHistory,
  speechToText,
};
