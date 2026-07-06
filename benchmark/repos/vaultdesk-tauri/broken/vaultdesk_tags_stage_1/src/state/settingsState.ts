import {
  normalizeSettings,
  CURRENT_SETTINGS_VERSION,
  type SettingsView,
} from "../api/settings.ts";

// In-memory holder for the active settings.
export class SettingsState {
  private settings: SettingsView = {
    version: CURRENT_SETTINGS_VERSION,
    theme: "light",
    vaultRoot: "",
    extra: {},
  };

  get(): SettingsView {
    return { ...this.settings, extra: { ...this.settings.extra } };
  }

  set(raw: any): void {
    this.settings = normalizeSettings(raw);
  }

  getTheme(): string {
    return this.settings.theme;
  }
}
