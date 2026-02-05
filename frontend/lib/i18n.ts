// Internationalization (i18n) support
export type Language = 'zh' | 'ja' | 'en';

export const translations = {
  zh: {
    // Header
    connected: '已连接',
    notConnected: '未连接',
    settings: '设置',
    connectZoho: '连接 Zoho',
    syncEmails: '同步邮件',
    syncing: '同步中...',
    syncAndLearn: '同步并学习',
    analyzing: '分析中...',
    analyzePriority: '分析重点',

    // Filter tabs
    all: '全部',
    pending: '待处理',
    processed: '已完成',
    priority: '重点',

    // Email detail
    noEmailSelected: '未选择邮件',
    selectEmailHint: '从列表中选择一封邮件查看详情',

    // Skill library
    skillLibrary: '技能库',
    skillsLoaded: '个技能已加载',
    keywords: '关键词',

    // Reply editor
    generateReply: '生成回复',
    generating: '生成中...',
    send: '发送',
    sending: '发送中...',

    // Sync modal
    syncOptions: '同步选项',
    syncRange: '同步范围',
    last7days: '最近7天',
    last30days: '最近30天',
    last90days: '最近90天',
    clearAll: '清空全部',
    cancel: '取消',
    confirm: '确认',

    // Loading
    loading: '加载中...',
    loadingInbox: '正在加载收件箱...',

    // Language
    language: '语言',

    // Skill Library
    categories: '分类',
    totalUsage: '总使用',
    noSkillsYet: '还没有技能',
    syncToGenerateSkills: '同步邮件并运行学习以生成技能',
    skillDescription: '技能描述',
    triggerKeywords: '触发关键词',
    more: '更多',
    processingRules: '处理规则',
    rule: '规则',
    moreRules: '还有 {count} 条规则...',
    successRate: '成功率',
    status: '状态',
    enabled: '启用',
    disabled: '禁用',
    sourceEmails: '来源邮件',
    initialLearning: '初学',
    evolution: '进化',
    moreSourceEmails: '还有 {count} 封来源邮件...',
    noSourceEmails: '暂无来源邮件记录',
    usageCount: '次使用',
  },
  ja: {
    // Header
    connected: '接続済み',
    notConnected: '未接続',
    settings: '設定',
    connectZoho: 'Zoho 接続',
    syncEmails: 'メール同期',
    syncing: '同期中...',
    syncAndLearn: '同期＆学習',
    analyzing: '分析中...',
    analyzePriority: '重要度分析',

    // Filter tabs
    all: 'すべて',
    pending: '未処理',
    processed: '完了',
    priority: '重要',

    // Email detail
    noEmailSelected: 'メールを選択してください',
    selectEmailHint: 'リストからメールを選択すると詳細が表示されます',

    // Skill library
    skillLibrary: 'スキルライブラリ',
    skillsLoaded: '個のスキルがロード済み',
    keywords: 'キーワード',

    // Reply editor
    generateReply: '返信を生成',
    generating: '生成中...',
    send: '送信',
    sending: '送信中...',

    // Sync modal
    syncOptions: '同期オプション',
    syncRange: '同期範囲',
    last7days: '過去7日間',
    last30days: '過去30日間',
    last90days: '過去90日間',
    clearAll: 'すべて削除',
    cancel: 'キャンセル',
    confirm: '確認',

    // Loading
    loading: '読み込み中...',
    loadingInbox: '受信トレイを読み込んでいます...',

    // Language
    language: '言語',

    // Skill Library
    categories: 'カテゴリ',
    totalUsage: '総使用数',
    noSkillsYet: 'スキルがありません',
    syncToGenerateSkills: 'メールを同期して学習を実行するとスキルが生成されます',
    skillDescription: 'スキル説明',
    triggerKeywords: 'トリガーキーワード',
    more: 'もっと',
    processingRules: '処理ルール',
    rule: 'ルール',
    moreRules: '他に {count} 件のルール...',
    successRate: '成功率',
    status: 'ステータス',
    enabled: '有効',
    disabled: '無効',
    sourceEmails: 'ソースメール',
    initialLearning: '初期学習',
    evolution: '進化',
    moreSourceEmails: '他に {count} 件のソースメール...',
    noSourceEmails: 'ソースメールの記録がありません',
    usageCount: '回使用',
  },
  en: {
    // Header
    connected: 'Connected',
    notConnected: 'Not connected',
    settings: 'Settings',
    connectZoho: 'Connect Zoho',
    syncEmails: 'Sync Emails',
    syncing: 'Syncing...',
    syncAndLearn: 'Sync & Learn',
    analyzing: 'Analyzing...',
    analyzePriority: 'Analyze Priority',

    // Filter tabs
    all: 'All',
    pending: 'Pending',
    processed: 'Processed',
    priority: 'Priority',

    // Email detail
    noEmailSelected: 'No email selected',
    selectEmailHint: 'Select an email from the list to view details',

    // Skill library
    skillLibrary: 'Skill Library',
    skillsLoaded: 'skills loaded',
    keywords: 'Keywords',

    // Reply editor
    generateReply: 'Generate Reply',
    generating: 'Generating...',
    send: 'Send',
    sending: 'Sending...',

    // Sync modal
    syncOptions: 'Sync Options',
    syncRange: 'Sync Range',
    last7days: 'Last 7 days',
    last30days: 'Last 30 days',
    last90days: 'Last 90 days',
    clearAll: 'Clear All',
    cancel: 'Cancel',
    confirm: 'Confirm',

    // Loading
    loading: 'Loading...',
    loadingInbox: 'Loading your inbox...',

    // Language
    language: 'Language',

    // Skill Library
    categories: 'Categories',
    totalUsage: 'Total Usage',
    noSkillsYet: 'No skills yet',
    syncToGenerateSkills: 'Sync emails and run learning to generate skills',
    skillDescription: 'Description',
    triggerKeywords: 'Trigger Keywords',
    more: 'more',
    processingRules: 'Processing Rules',
    rule: 'Rule',
    moreRules: '{count} more rules...',
    successRate: 'Success Rate',
    status: 'Status',
    enabled: 'Enabled',
    disabled: 'Disabled',
    sourceEmails: 'Source Emails',
    initialLearning: 'Initial',
    evolution: 'Evolution',
    moreSourceEmails: '{count} more source emails...',
    noSourceEmails: 'No source email records',
    usageCount: 'uses',
  },
};

export type TranslationKey = keyof typeof translations.zh;

export function getTranslation(lang: Language, key: TranslationKey): string {
  return translations[lang][key] || translations.en[key] || key;
}

export const languageNames: Record<Language, string> = {
  zh: '中文',
  ja: '日本語',
  en: 'English',
};

export const languageFlags: Record<Language, string> = {
  zh: '🇨🇳',
  ja: '🇯🇵',
  en: '🇺🇸',
};
