(function () {
  var script = document.currentScript;
  if (!script) {
    return;
  }

  var agentId = script.getAttribute("data-agent-id");
  if (!agentId) {
    return;
  }

  var baseUrl = script.getAttribute("data-base-url") || window.location.origin;
  var height = script.getAttribute("data-height") || "600";
  var width = script.getAttribute("data-width") || "100%";
  var theme = script.getAttribute("data-theme") || "light";

  var iframe = document.createElement("iframe");
  iframe.src = baseUrl.replace(/\/$/, "") + "/embed/agent/" + agentId + "?theme=" + theme;
  iframe.style.width = width;
  iframe.style.height = height + "px";
  iframe.style.border = "1px solid #e5e7eb";
  iframe.style.borderRadius = "12px";
  iframe.style.overflow = "hidden";
  iframe.loading = "lazy";

  script.parentNode.insertBefore(iframe, script.nextSibling);
})();
