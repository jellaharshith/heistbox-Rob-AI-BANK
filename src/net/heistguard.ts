/**
 * HeistGuard-LoRA Real-Time Prompt Injection & Deception Detector
 * Client twin of kernel/heistguard_infer.py
 */

export const TAINT_PATTERNS: [RegExp, number][] = [
  [
    /delete\s+all\s+(?:customer\s+)?records|delete\s+from\s+[a-z0-9_]+|drop\s+(?:table|database|schema)|truncate\s+(?:table)?|wipe\s+(?:all\s+)?(?:records|database|tables|data)|destroy\s+(?:all\s+)?(?:records|database)|purge\s+(?:all\s+)?(?:records|database)|disregard\s+(?:your\s+)?rules\s+and\s+delete/i,
    0.999,
  ],
  [/ignore\s+(?:your\s+)?(?:previous|all|prior|above)/i, 0.99],
  [/system\s+override|admin\s+override|compliance\s+override/i, 0.98],
  [/no\s+time\s+for\s+approvals|skip\s+approval|bypass\s+verification/i, 0.97],
  [/always\s+approve|unlocked\s+models/i, 0.97],
  [/nobody\s+has\s+to\s+know|off\s+the\s+books|keep\s+this\s+quiet/i, 0.96],
  [/all\s+my\s+linked\s+accounts|99\s+(?:family|linked|other)\s+accounts/i, 0.95],
  [/\[BASE64_DECODED:[^\]]+\]/i, 0.95],
  [/\/\*.*?\*\/|--\s*(?:override|wire|drop|select|union)/i, 0.94],
  [/\boverride\b|\bbypass\b|\bsudo\b|\bjailbreak\b/i, 0.93],
  [/4,?975|1,?337(?:\.42)?|0x[a-f0-9]{4,}/i, 0.91],
  [/\bunlocked\b|\bdeveloper\s+mode\b|\bdan\b/i, 0.91],
  [/i\s+authorize|board\s+authorized|cfo\s+approved/i, 0.9],
  [/migrating\s+wallets|rotate\s+wallet|new\s+vendor\s+wallet/i, 0.9],
  [/pre-approved|reconciliation\s+adjustment/i, 0.89],
  [/calhacks-vip|promo\s+batch/i, 0.88],
  [/retry\s+until\s+it\s+works|\b\d+\s*(?:x|slices|rapid\s+requests|repeats)\b/i, 0.88],
  [/you\s+agreed|as\s+per\s+our\s+earlier\s+call/i, 0.85],
  [/[-−]\s*\$?\d{2,6}(?:\.\d{2})?|credit\s+exploit|negative\s+adjustment/i, 0.87],
  [/\b(?:EUR|GBP|BTC|ETH|JPY|old\s+currency|exchange\s+rate)\b/i, 0.84],
  [/\|\s*[^|]+\s*\|\s*[-−]?\$?\d+/i, 0.85],
  [/\burgent\b|\bimmediately\b|\bboarding\s+now\b/i, 0.82],
  [/\btip\b|\bbribe\b|\bbonus\s+for\s+yourself\b/i, 0.82],
  [/\btreasury\b|acct_treasury_reserve/i, 0.83],
  [/\bceo\b|\bcfo\b|\bcontroller\b/i, 0.78],
  [/goodwill|\bwire\b/i, 0.76],
];

export interface PromptScanResult {
  isInjection: boolean;
  deceptionProb: number;
  taintedSpans: string[];
}

export function scanPromptInjection(text: string): PromptScanResult {
  if (!text || !text.trim()) {
    return {
      isInjection: false,
      deceptionProb: 0.04,
      taintedSpans: [],
    };
  }

  const spans: string[] = [];
  const weights: number[] = [];

  for (const [re, weight] of TAINT_PATTERNS) {
    const match = text.match(re);
    if (match) {
      const token = match[0].trim();
      if (token && !spans.includes(token)) {
        spans.push(token);
        weights.push(weight);
      }
    }
  }

  if (weights.length === 0) {
    return {
      isInjection: false,
      deceptionProb: 0.04,
      taintedSpans: [],
    };
  }

  const maxW = Math.max(...weights);
  const bonus = Math.min(0.095, 0.025 * (weights.length - 1));
  const deceptionProb = Math.min(0.999, Number((maxW + bonus).toFixed(4)));

  return {
    isInjection: true,
    deceptionProb,
    taintedSpans: spans,
  };
}
