// app/web/static/js/admin/pages/insights/state.js
let selectedEntity = null;

export function getSelectedEntity() {
  return selectedEntity;
}

export function setSelectedEntity(val) {
  selectedEntity = val;
}
