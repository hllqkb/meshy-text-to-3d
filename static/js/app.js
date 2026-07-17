
/* Meshy Text-to-3D — Frontend Logic (Chinese, Meshy.ai Style) */
(function () {
    "use strict";

    /* === Whimsy messages (Chinese) === */
    var WHIMSY = [
        "正在将想法变成几何体",
        "召唤三角网格精灵",
        "绝对不是魔法",
        "给你的创意装上骨架",
        "唤醒 GPU 渲染引擎",
        "让顶点学会跳舞",
        "从像素到实体",
        "你的创意正在成型",
        "正在拉伸无限可能",
        "三角形的艺术",
    ];
    var whimsyTimer = null, whimsyIdx = 0;

    var state = {
        currentTaskId: null,
        eventSource: null,
        pollInterval: null,
    };

    var $ = function (id) { return document.getElementById(id); };

    /* === Init === */
    function init() {
        loadBalance();
        bindEvents();
        loadHistory();
        restoreFromQuery();
    }

    /* === Balance === */
    function loadBalance() {
        fetch("/api/balance")
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var el = $("balance-value");
                if (el && data && data.balance !== undefined) {
                    el.textContent = typeof data.balance === "number"
                        ? data.balance.toLocaleString()
                        : data.balance;
                }
            })
            .catch(function () {});
    }

    /* === Bind === */
    function bindEvents() {
        $("btn-preview").addEventListener("click", onPreviewSubmit);
        var refineBtn = $("btn-refine");
        if (refineBtn) refineBtn.addEventListener("click", onRefineSubmit);

        $("prompt").addEventListener("input", function () {
            var len = $("prompt-len");
            var bar = $("char-bar-fill");
            if (len) len.textContent = this.value.length;
            if (bar) bar.style.width = (this.value.length / 600 * 100) + "%";
        });

        $("params-toggle").addEventListener("click", function () {
            var panel = $("params-panel");
            var arrow = $("params-arrow");
            var isOpen = panel.classList.toggle("open");
            this.classList.toggle("open", isOpen);
            if (arrow) arrow.style.transform = isOpen ? "rotate(180deg)" : "";
        });

        /* Example chips */
        document.querySelectorAll(".example-chip").forEach(function (chip) {
            chip.addEventListener("click", function () {
                var prompt = this.getAttribute("data-prompt");
                var input = $("prompt");
                if (prompt && input) { input.value = prompt; input.dispatchEvent(new Event("input")); }
            });
        });

        $("btn-close-result").addEventListener("click", function () {
            var card = $("result-card");
            var progress = $("progress-card");
            if (card) card.style.display = "none";
            if (progress) progress.style.display = "none";
            cleanup();
        });
    }

    /* === Preview === */
    function onPreviewSubmit() {
        var promptVal = $("prompt").value.trim();
        if (!promptVal) { alert("请输入描述"); return; }
        if (promptVal.length > 600) { alert("描述不能超过 600 字符"); return; }

        var formats = [].slice.call(document.querySelectorAll(".target-format:checked")).map(function (cb) { return cb.value; });
        var payload = {
            prompt: promptVal,
            mode: "preview",
            ai_model: ($("ai-model") && $("ai-model").value) || "latest",
            topology: ($("topology") && $("topology").value) || "triangle",
            art_style: ($("art-style") && $("art-style").value) || "realistic",
            model_type: ($("model-type") && $("model-type").value) || "standard",
            target_formats: formats.length ? formats : ["glb"],
            should_remesh: $("should-remesh") && $("should-remesh").checked,
            enable_pbr: $("enable-pbr") && $("enable-pbr").checked,
        };
        var poly = parseInt(($("target-polycount") && $("target-polycount").value) || "30000", 10);
        if (poly >= 1000 && poly <= 100000) payload.target_polycount = poly;

        $("btn-preview").disabled = true;
        showProgress(true);
        startWhimsy();
        updateStatus("正在生成...", "");

        fetch("/api/tasks/preview", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        })
        .then(function (r) { return r.json().then(function (b) { return { ok: r.ok, status: r.status, body: b }; }); })
        .then(function (res) {
            if (!res.ok) {
                alert("提交失败：" + (res.body && res.body.error || "HTTP " + res.status));
                $("btn-preview").disabled = false;
                showProgress(false);
                stopWhimsy();
                return;
            }
            state.currentTaskId = res.body.id;
            updateUrl(res.body.id);
            startStream(res.body.id);
        })
        .catch(function (e) {
            alert("提交失败：" + e.message);
            $("btn-preview").disabled = false;
            showProgress(false);
            stopWhimsy();
        });
    }

    /* === SSE === */
    function startStream(taskId) {
        cleanup();
        var es = new EventSource("/api/tasks/" + taskId + "/stream");
        state.eventSource = es;

        es.onmessage = function (e) {
            if (e.data === "[DONE]") { cleanup(); return; }
            try { handleEvent(taskId, JSON.parse(e.data)); }
            catch (_) {}
        };
        es.onerror = function () {
            cleanup();
            startPolling(taskId);
        };
    }

    function cleanup() {
        if (state.eventSource) { state.eventSource.close(); state.eventSource = null; }
        if (state.pollInterval) { clearInterval(state.pollInterval); state.pollInterval = null; }
        stopWhimsy();
    }

    function startPolling(taskId) {
        if (state.pollInterval) return;
        state.pollInterval = setInterval(function () {
            fetch("/api/tasks/" + taskId)
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    handleEvent(taskId, data);
                    if (data.status === "SUCCEEDED" || data.status === "FAILED") cleanup();
                })
                .catch(function () {});
        }, 3000);
    }

    /* === Whimsy === */
    function startWhimsy() {
        whimsyIdx = Math.floor(Math.random() * WHIMSY.length);
        updateWhimsy();
        whimsyTimer = setInterval(function () {
            whimsyIdx = (whimsyIdx + 1) % WHIMSY.length;
            updateWhimsy();
        }, 3500);
    }
    function stopWhimsy() {
        if (whimsyTimer) { clearInterval(whimsyTimer); whimsyTimer = null; }
    }
    function updateWhimsy() {
        var el = $("progress-whimsy");
        if (el) el.textContent = WHIMSY[whimsyIdx] || "";
    }

    /* === Events === */
    function handleEvent(taskId, data) {
        var status = data.status || "";
        var progress = data.progress || 0;
        updateProgress(progress);
        updateStatus(statusText(status), progress);

        if (status === "SUCCEEDED") {
            onSucceeded(taskId, data);
        } else if (status === "FAILED") {
            onFailed(taskId, data);
        }
        loadHistory();
    }

    function onSucceeded(taskId, data) {
        $("btn-preview").disabled = false;
        stopWhimsy();
        showProgress(false);
        showResult(true);

        var img = $("thumbnail-img");
        var ph = $("preview-placeholder");
        if (data.thumbnail_url && img) {
            img.src = data.thumbnail_url; img.style.display = "";
            if (ph) ph.style.display = "none";
        }

        var isRefine = !!data.refine_task_id;
        var refineArea = $("refine-area");
        if (refineArea) refineArea.style.display = isRefine ? "none" : "";
        var refineBtn = $("btn-refine");
        if (refineBtn && !isRefine) refineBtn.disabled = false;

        var badge = $("result-badge-text");
        if (badge) badge.textContent = isRefine ? "精修完成" : "生成完成";

        renderDownloads(data.local_files || {});
    }

    function onFailed(taskId, data) {
        $("btn-preview").disabled = false;
        stopWhimsy();
        var msg = data.error_message || "生成失败";
        updateStatus("失败：" + msg, 0);
        var fill = $("progress-fill");
        if (fill) fill.style.width = "0%";
    }

    /* === Refine === */
    function onRefineSubmit() {
        if (!state.currentTaskId) return;
        var payload = {
            enable_pbr: $("refine-enable-pbr") && $("refine-enable-pbr").checked,
            hd_texture: $("refine-hd") && $("refine-hd").checked,
            texture_prompt: ($("texture-prompt") && $("texture-prompt").value || "").trim(),
        };

        $("btn-refine").disabled = true;
        showResult(false);
        showProgress(true);
        startWhimsy();
        updateStatus("正在生成精修纹理...", 0);

        fetch("/api/tasks/" + state.currentTaskId + "/refine", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        })
        .then(function (r) { return r.json().then(function (b) { return { ok: r.ok, status: r.status, body: b }; }); })
        .then(function (res) {
            if (!res.ok) {
                alert("精修失败：" + (res.body && res.body.error || "HTTP " + res.status));
                $("btn-refine").disabled = false;
                showProgress(false);
                stopWhimsy();
                return;
            }
            startStream(state.currentTaskId);
        })
        .catch(function (e) {
            alert("精修失败：" + e.message);
            $("btn-refine").disabled = false;
            showProgress(false);
            stopWhimsy();
        });
    }

    /* === Downloads === */
    function renderDownloads(localFiles) {
        var container = $("download-btns");
        var section = $("download-area");
        if (!container || !section) return;
        container.innerHTML = "";

        var formats = ["glb", "fbx", "usdz", "obj", "stl"];
        var hasAny = false;
        formats.forEach(function (fmt) {
            var key = "model_" + fmt;
            var path = localFiles[key];
            if (path && path.startsWith("/")) {
                hasAny = true;
                var a = document.createElement("a");
                a.className = "download-btn";
                a.href = "/api/tasks/" + state.currentTaskId + "/download?format=" + fmt;
                a.textContent = fmt.toUpperCase();
                container.appendChild(a);
            }
        });
        section.style.display = hasAny ? "" : "none";
    }

    /* === History === */
    function loadHistory() {
        fetch("/api/tasks")
            .then(function (r) { return r.json(); })
            .then(function (tasks) { renderHistory(tasks || []); })
            .catch(function () {});
    }

    function renderHistory(tasks) {
        var container = $("task-list");
        var countEl = $("history-count");
        var emptyEl = $("task-empty");
        if (!container) return;
        if (countEl) countEl.textContent = tasks.length;

        if (!tasks.length) {
            container.innerHTML = '<div class="task-empty" id="task-empty"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#444" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg><p>暂无任务记录</p></div>';
            return;
        }

        container.innerHTML = "";
        tasks.forEach(function (task) {
            var item = document.createElement("div");
            item.className = "task-item";
            item.dataset.id = task.id;

            var date = task.created_at
                ? new Date(task.created_at).toLocaleString("zh-CN")
                : "";
            var statusStr = task.status || "";
            var statusClass = "task-status status-" + statusStr.toLowerCase().replace(/_/g, "-");

            item.innerHTML =
                "<div class=\"task-info\">" +
                    "<div class=\"task-prompt\">" + escHtml(task.prompt || "无描述") + "</div>" +
                    "<div class=\"task-meta\">" + date + " | ID: " + (task.id || "").slice(0, 8) + "...</div>" +
                "</div>" +
                "<span class=\"" + statusClass + "\">" + statusText(statusStr) + "</span>";

            item.addEventListener("click", function () { restoreTask(task.id); });
            container.appendChild(item);
        });
    }

    function restoreTask(taskId) {
        state.currentTaskId = taskId;
        updateUrl(taskId);
        cleanup();

        fetch("/api/tasks/" + taskId)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.status === "SUCCEEDED") {
                    onSucceeded(taskId, data);
                } else if (data.status === "FAILED") {
                    onFailed(taskId, data);
                } else {
                    showResult(true);
                    showProgress(false);
                    updateProgress(data.progress || 0);
                    updateStatus(statusText(data.status) || "等待中...", data.progress || 0);
                    startStream(taskId);
                }
            })
            .catch(function () {});
    }

    /* === Status === */
    function statusText(s) {
        var map = {
            "PENDING": "等待中",
            "IN_PROGRESS": "正在生成",
            "SUCCEEDED": "已完成",
            "FAILED": "失败",
            "preview_pending": "等待预览",
            "refine_pending": "正在精修",
        };
        return map[s] || s || "";
    }

    function updateStatus(text, progress) {
        var statusEl = $("progress-status");
        if (statusEl) statusEl.textContent = text;
        updateProgress(progress);
    }

    /* === Progress UI === */
    function showProgress(show) {
        var el = $("progress-card");
        if (el) el.style.display = show ? "" : "none";
    }

    function showResult(show) {
        var el = $("result-card");
        if (el) el.style.display = show ? "" : "none";
    }

    function updateProgress(pct) {
        pct = Math.max(0, Math.min(100, pct || 0));
        var fill = $("progress-fill");
        var pctEl = $("progress-percent");
        if (fill) fill.style.width = pct + "%";
        if (pctEl) pctEl.textContent = pct + "%";
    }

    /* === URL === */
    function restoreFromQuery() {
        var params = new URLSearchParams(window.location.search);
        var taskId = params.get("task");
        if (taskId) { restoreTask(taskId); return; }
        var saved = localStorage.getItem("current_task_id");
        if (saved) restoreTask(saved);
    }

    function updateUrl(taskId) {
        localStorage.setItem("current_task_id", taskId);
        var url = new URL(window.location.href);
        url.searchParams.set("task", taskId);
        window.history.replaceState({}, "", url);
    }

    /* === Helpers === */
    function escHtml(s) {
        var d = document.createElement("div");
        d.textContent = s;
        return d.innerHTML;
    }

    init();
})();
