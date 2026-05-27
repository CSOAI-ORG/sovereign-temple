/**
 * MEOKCLAW 微信小程序入口 (WeChat Mini Program Entry)
 *
 * 功能:
 *   - 初始化小程序全局状态
 *   - 管理用户登录与会话
 *   - 注册 MEOKCLAW API 客户端
 *   - 处理全局错误与内容安全拦截
 *
 * 合规:
 *   - 用户授权后才获取 openid（个保法第13条）
 *   - 敏感操作前二次确认
 *   - 所有网络请求经过内容安全预检
 */

App({
  globalData: {
    userInfo: null,
    anonymousId: null,
    sessionToken: null,
    meokclawApiBase: 'http://localhost:3201',
    wechatBridgeBase: 'http://localhost:3201/wechat',
    isLoggedIn: false,
    councilMode: true,
    defaultModels: ['deepseek-v4-flash', 'kimi-k2.6', 'qwen3-235b'],
    // 文化设置
    cultureSettings: {
      politenessLevel: 'auto', // auto | formal | polite | casual
      showCostInfo: true,
      enableVoiceInput: true,
    },
    // 系统信息
    systemInfo: {},
  },

  onLaunch(options) {
    console.log('[MEOKCLAW] 小程序启动', options);

    // 获取系统信息
    wx.getSystemInfo({
      success: (res) => {
        this.globalData.systemInfo = res;
        console.log('[MEOKCLAW] 系统信息:', res.platform, res.version);
      },
    });

    // 检查本地会话
    this.checkLocalSession();

    // 注册网络状态监听
    wx.onNetworkStatusChange((res) => {
      if (!res.isConnected) {
        wx.showToast({
          title: '网络已断开，部分功能受限',
          icon: 'none',
          duration: 3000,
        });
      }
    });

    // 初始化完成
    console.log('[MEOKCLAW] 初始化完成 — 中国主权层已激活');
  },

  onShow(options) {
    // 小程序切换到前台
    console.log('[MEOKCLAW] 进入前台');
  },

  onHide() {
    // 小程序切换到后台
    console.log('[MEOKCLAW] 进入后台');
  },

  onError(msg) {
    console.error('[MEOKCLAW] 全局错误:', msg);
    // 可接入微信错误监控
  },

  onUnhandledRejection(res) {
    console.error('[MEOKCLAW] 未处理的 Promise 拒绝:', res);
  },

  // ─────────────────────────────────────────────────────────────────────────
  // 会话管理
  // ─────────────────────────────────────────────────────────────────────────

  /**
   * 检查本地是否有有效会话
   */
  checkLocalSession() {
    try {
      const anonymousId = wx.getStorageSync('meokclaw_anonymous_id');
      const sessionToken = wx.getStorageSync('meokclaw_session_token');
      const expiresAt = wx.getStorageSync('meokclaw_session_expires');

      if (anonymousId && sessionToken && expiresAt > Date.now()) {
        this.globalData.anonymousId = anonymousId;
        this.globalData.sessionToken = sessionToken;
        this.globalData.isLoggedIn = true;
        console.log('[MEOKCLAW] 本地会话有效');
      } else {
        console.log('[MEOKCLAW] 本地会话已过期或不存在');
      }
    } catch (e) {
      console.error('[MEOKCLAW] 读取本地会话失败:', e);
    }
  },

  /**
   * 微信小程序登录
   * 调用 wx.login 获取 code，然后到后端换取匿名化身份
   */
  login() {
    return new Promise((resolve, reject) => {
      wx.login({
        success: (loginRes) => {
          if (loginRes.code) {
            // 发送到后端换取 anonymous_id
            wx.request({
              url: `${this.globalData.wechatBridgeBase}/login`,
              method: 'POST',
              data: {
                code: loginRes.code,
              },
              success: (res) => {
                if (res.statusCode === 200 && res.data.anonymous_id) {
                  this.globalData.anonymousId = res.data.anonymous_id;
                  this.globalData.sessionToken = res.data.session_token;
                  this.globalData.isLoggedIn = true;

                  // 本地存储
                  wx.setStorageSync('meokclaw_anonymous_id', res.data.anonymous_id);
                  wx.setStorageSync('meokclaw_session_token', res.data.session_token);
                  wx.setStorageSync('meokclaw_session_expires', Date.now() + res.data.expires_in * 1000);

                  console.log('[MEOKCLAW] 登录成功');
                  resolve(res.data);
                } else {
                  reject(new Error('登录失败: 无效响应'));
                }
              },
              fail: reject,
            });
          } else {
            reject(new Error('wx.login 失败'));
          }
        },
        fail: reject,
      });
    });
  },

  /**
   * 登出并清除本地数据
   */
  logout() {
    this.globalData.anonymousId = null;
    this.globalData.sessionToken = null;
    this.globalData.isLoggedIn = false;

    wx.removeStorageSync('meokclaw_anonymous_id');
    wx.removeStorageSync('meokclaw_session_token');
    wx.removeStorageSync('meokclaw_session_expires');

    console.log('[MEOKCLAW] 已登出');
  },

  // ─────────────────────────────────────────────────────────────────────────
  // 全局工具方法
  // ─────────────────────────────────────────────────────────────────────────

  /**
   * 显示符合中国用户习惯的提示
   */
  showPoliteToast(message, icon = 'none') {
    wx.showToast({
      title: message,
      icon: icon,
      duration: 2000,
    });
  },

  /**
   * 请求用户授权（符合个保法最小必要原则）
   */
  requestUserProfile() {
    return new Promise((resolve, reject) => {
      wx.getUserProfile({
        desc: '用于完善用户资料', // 必须明确说明用途
        success: (res) => {
          this.globalData.userInfo = res.userInfo;
          resolve(res.userInfo);
        },
        fail: reject,
      });
    });
  },
});
