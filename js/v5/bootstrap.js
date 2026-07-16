"use strict";

(function () {
  const v5 = window.NBAVL.v5;

  function prepare() {
    v5.modules.drawer.ensure();
    document.documentElement.dataset.uiPreparing = "true";
  }

  function afterRender() {
    v5.modules.dashboard.afterRender();
    document.documentElement.dataset.uiPreparing = "false";
    document.documentElement.dataset.uiReady = "true";
  }

  v5.prepare = prepare;
  v5.afterRender = afterRender;
}());
