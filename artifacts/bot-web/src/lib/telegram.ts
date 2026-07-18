// Telegram Mini App SDK helpers
// The SDK is loaded via CDN in index.html

declare global {
  interface Window {
    Telegram?: {
      WebApp: {
        initData: string;
        initDataUnsafe: {
          user?: {
            id: number;
            first_name: string;
            last_name?: string;
            username?: string;
            language_code?: string;
          };
          start_param?: string;
        };
        colorScheme: 'light' | 'dark';
        themeParams: Record<string, string>;
        isExpanded: boolean;
        viewportHeight: number;
        viewportStableHeight: number;
        ready(): void;
        expand(): void;
        close(): void;
        showAlert(message: string, callback?: () => void): void;
        showConfirm(message: string, callback: (confirmed: boolean) => void): void;
        HapticFeedback: {
          impactOccurred(style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'): void;
          notificationOccurred(type: 'error' | 'success' | 'warning'): void;
          selectionChanged(): void;
        };
        BackButton: {
          isVisible: boolean;
          show(): void;
          hide(): void;
          onClick(callback: () => void): void;
          offClick(callback: () => void): void;
        };
        MainButton: {
          text: string;
          isVisible: boolean;
          show(): void;
          hide(): void;
          setText(text: string): void;
          onClick(callback: () => void): void;
          offClick(callback: () => void): void;
          showProgress(leaveActive?: boolean): void;
          hideProgress(): void;
        };
        openTelegramLink(url: string): void;
        openLink(url: string): void;
        copyTextToClipboard(text: string, callback?: (success: boolean) => void): void;
      };
    };
  }
}

export const twa = window.Telegram?.WebApp;

export function getInitData(): string {
  return twa?.initData || '';
}

export function getTgUser() {
  return twa?.initDataUnsafe?.user || null;
}

export function isInTelegram(): boolean {
  return !!twa && !!twa.initData;
}

export function haptic(type: 'success' | 'error' | 'warning' | 'light' | 'medium' | 'heavy' = 'light') {
  if (!twa) return;
  if (type === 'success' || type === 'error' || type === 'warning') {
    twa.HapticFeedback.notificationOccurred(type);
  } else {
    twa.HapticFeedback.impactOccurred(type);
  }
}

export function copyText(text: string): Promise<boolean> {
  return new Promise((resolve) => {
    if (twa?.copyTextToClipboard) {
      twa.copyTextToClipboard(text, resolve);
    } else {
      navigator.clipboard.writeText(text).then(() => resolve(true)).catch(() => resolve(false));
    }
  });
}

export function shareLink(url: string) {
  if (twa) {
    twa.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(url)}`);
  } else {
    window.open(`https://t.me/share/url?url=${encodeURIComponent(url)}`, '_blank');
  }
}

// Call this once on app mount
export function initTelegramApp() {
  if (twa) {
    twa.ready();
    twa.expand();
  }
}
