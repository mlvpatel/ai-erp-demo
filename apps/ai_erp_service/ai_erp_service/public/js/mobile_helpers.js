/* Offline draft helper — NOT a shipped product surface.
 *
 * IndexedDB sync/scope is unfinished. Keep this module inert until a tracked
 * feature flag and sync path exist. Do not wire it through app_include_js.
 */
const OFFLINE_DRAFTS_ENABLED = false;

function offline_drafts_unavailable() {
  return {
    enabled: false,
    reason: "Offline drafts are not shipped; sync and permission scope are unfinished.",
  };
}

async function save_offline_draft(_work_order_name, _draft_data) {
  return false;
}

async function get_offline_draft(_work_order_name) {
  return null;
}

async function clear_offline_draft(_work_order_name) {
  return;
}

if (typeof window !== "undefined") {
  window.AI_ERP_OFFLINE_DRAFTS = offline_drafts_unavailable();
  if (OFFLINE_DRAFTS_ENABLED) {
    window.save_offline_draft = save_offline_draft;
    window.get_offline_draft = get_offline_draft;
    window.clear_offline_draft = clear_offline_draft;
  }
}
