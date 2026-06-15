let globalInsightsData = null;

export function getState() {
    return globalInsightsData;
}

export function setState(data) {
    globalInsightsData = data;
}
