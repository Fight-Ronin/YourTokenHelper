import { invoke } from "@tauri-apps/api/core";

import {
  CLEAR_SAVED_SOURCE_ROOTS_COMMAND,
  LOAD_SAVED_SOURCE_ROOTS_COMMAND,
  SAVE_SOURCE_ROOTS_COMMAND,
  defaultSourceRootPreferences,
  savedSourceRootsPayloadFromPreferences,
  sourceRootPreferencesFromSaved,
  type SavedSourceRootsPayload,
  type SourceRootPreferences
} from "./sourceRootPreferences.js";

export type SourceRootPreferencesOutcome =
  | {
      ok: true;
      preferences: SourceRootPreferences;
    }
  | {
      ok: false;
      preferences: SourceRootPreferences;
      message: string;
    };

export async function loadSourceRootPreferences(): Promise<SourceRootPreferencesOutcome> {
  try {
    const saved = await invoke<SavedSourceRootsPayload>(LOAD_SAVED_SOURCE_ROOTS_COMMAND);
    return {
      ok: true,
      preferences: sourceRootPreferencesFromSaved(saved)
    };
  } catch {
    return {
      ok: false,
      preferences: defaultSourceRootPreferences(),
      message: "Saved roots unavailable"
    };
  }
}

export async function saveSourceRootPreferences(
  preferences: SourceRootPreferences
): Promise<SourceRootPreferencesOutcome> {
  try {
    const saved = await invoke<SavedSourceRootsPayload>(SAVE_SOURCE_ROOTS_COMMAND, {
      args: savedSourceRootsPayloadFromPreferences(preferences)
    });
    return {
      ok: true,
      preferences: sourceRootPreferencesFromSaved(saved)
    };
  } catch {
    return {
      ok: false,
      preferences,
      message: "Saved roots unavailable"
    };
  }
}

export async function clearSourceRootPreferences(): Promise<SourceRootPreferencesOutcome> {
  try {
    const saved = await invoke<SavedSourceRootsPayload>(CLEAR_SAVED_SOURCE_ROOTS_COMMAND);
    return {
      ok: true,
      preferences: sourceRootPreferencesFromSaved(saved)
    };
  } catch {
    return {
      ok: false,
      preferences: defaultSourceRootPreferences(),
      message: "Saved roots unavailable"
    };
  }
}
