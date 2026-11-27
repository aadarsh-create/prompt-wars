let healthStatus = "checking";
let pendingRequests = 0;
let apiFailure = false;
const listeners = new Set();

function currentStatus() {
  if (pendingRequests > 0) return "waiting";
  if (apiFailure) return "offline";
  return healthStatus;
}

function notifyListeners() {
  const status = currentStatus();
  listeners.forEach((listener) => listener(status));
}

export function getServerStatus() {
  return currentStatus();
}

export function subscribeServerStatus(listener) {
  listeners.add(listener);
  listener(currentStatus());
  return () => listeners.delete(listener);
}

export function beginServerRequest({ healthCheck = false } = {}) {
  pendingRequests += 1;
  notifyListeners();
  let completed = false;

  function finish(result) {
    if (completed) return;
    completed = true;
    pendingRequests -= 1;

    if (healthCheck) {
      if (result === "success" || result === "failure") {
        healthStatus = result === "success" ? "online" : "offline";
      }
    } else if (result === "success") {
      apiFailure = false;
      healthStatus = "online";
    } else if (result === "failure") {
      apiFailure = true;
      healthStatus = "offline";
    }

    notifyListeners();
  }

  return {
    succeed: () => finish("success"),
    fail: () => finish("failure"),
    cancel: () => finish("cancel"),
  };
}
