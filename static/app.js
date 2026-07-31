"use strict";

(function () {
  const uploadForm = document.getElementById("upload-form");
  const videoFileInput = document.getElementById("video-file-input");
  const dropZone = document.getElementById("drop-zone");
  const dropTextContent = document.getElementById("drop-text-content");
  const redactModeSelect = document.getElementById("redact-mode-select");
  const detectFacesCb = document.getElementById("detect-faces-cb");
  const detectPlatesCb = document.getElementById("detect-plates-cb");
  const submitBtn = document.getElementById("submit-btn");
  const processStatusEl = document.getElementById("process-status");

  const outputPanel = document.getElementById("output-panel");
  const videoPreview = document.getElementById("video-preview");
  const downloadVideoBtn = document.getElementById("download-video-btn");
  const downloadReceiptBtn = document.getElementById("download-receipt-btn");

  const jobsListEl = document.getElementById("jobs-list");
  const clearHistoryBtn = document.getElementById("clear-history-btn");

  // Fetch Jobs on load
  fetchJobs();

  if (clearHistoryBtn) {
    clearHistoryBtn.addEventListener("click", async (e) => {
      e.preventDefault();
      if (
        confirm(
          "Vuoi davvero eliminare tutta la cronologia? (I video elaborati esportati sul disco NON verranno eliminati)"
        )
      ) {
        await clearHistory();
      }
    });
  }

  if (videoFileInput) {
    videoFileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files[0]) {
        updateFileLabel(e.target.files[0].name);
      }
    });
  }

  if (dropZone) {
    ["dragenter", "dragover"].forEach((evt) => {
      dropZone.addEventListener(evt, (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach((evt) => {
      dropZone.addEventListener(evt, (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
      });
    });

    dropZone.addEventListener("drop", (e) => {
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
        videoFileInput.files = e.dataTransfer.files;
        updateFileLabel(e.dataTransfer.files[0].name);
      }
    });
  }

  function updateFileLabel(name) {
    if (dropTextContent) {
      dropTextContent.innerHTML = `
        <span class="drop-icon">🎬</span>
        <strong>Video selezionato: ${name}</strong>
        <small>Pronto per l'oscuramento locale su CPU</small>
      `;
    }
  }

  if (uploadForm) {
    uploadForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!videoFileInput.files || !videoFileInput.files[0]) return;

      const file = videoFileInput.files[0];
      const mode = redactModeSelect ? redactModeSelect.value : "blur";
      const detectFaces = detectFacesCb ? detectFacesCb.checked : true;
      const detectPlates = detectPlatesCb ? detectPlatesCb.checked : true;

      const options = {
        mode: mode,
        detect_faces: detectFaces,
        detect_plates: detectPlates,
      };

      if (submitBtn) submitBtn.disabled = true;
      if (processStatusEl) {
        processStatusEl.textContent = "Caricamento video ed avvio elaborazione su CPU...";
        processStatusEl.className = "status-msg muted";
      }

      const formData = new FormData();
      formData.append("file", file);
      formData.append("engine", "video-privacy");
      formData.append("options", JSON.stringify(options));

      try {
        const res = await fetch("/api/jobs", {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          let errMsg = "Impossibile avviare l'elaborazione";
          if (typeof err.detail === "string") {
            errMsg = err.detail;
          } else if (Array.isArray(err.detail)) {
            errMsg = err.detail.map((d) => d.msg || JSON.stringify(d)).join(", ");
          }
          throw new Error(errMsg);
        }

        const job = await res.json();
        pollJobStatus(job.id);
      } catch (err) {
        if (processStatusEl) {
          processStatusEl.textContent = `Errore: ${err.message}`;
          processStatusEl.className = "status-msg error";
        }
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }

  // Poll Job Status
  async function pollJobStatus(jobId) {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        if (!res.ok) return;

        const job = await res.json();

        if (job.status === "running") {
          if (processStatusEl) {
            processStatusEl.textContent = "Elaborazione frame-by-frame in corso su CPU...";
            processStatusEl.className = "status-msg muted";
          }
        } else if (job.status === "completed") {
          clearInterval(interval);
          if (processStatusEl) {
            processStatusEl.textContent = `✅ ${job.summary || "Elaborazione video completata!"}`;
            processStatusEl.className = "status-msg success";
          }
          if (submitBtn) submitBtn.disabled = false;
          showResults(job);
          fetchJobs();
        } else if (job.status === "failed") {
          clearInterval(interval);
          if (processStatusEl) {
            processStatusEl.textContent = `Errore: ${job.error || "Elaborazione fallita"}`;
            processStatusEl.className = "status-msg error";
          }
          if (submitBtn) submitBtn.disabled = false;
        }
      } catch (err) {
        console.warn("Polling error:", err);
      }
    }, 1000);
  }

  // Show Results
  function showResults(job) {
    if (!job.artifacts || job.artifacts.length === 0) return;

    let videoArtifact = job.artifacts.find((a) => a.endsWith(".mp4"));
    let receiptArtifact = job.artifacts.find((a) => a.endsWith(".json"));

    if (videoArtifact) {
      const videoUrl = `/api/jobs/${job.id}/artifacts/${videoArtifact}`;
      if (videoPreview) {
        videoPreview.src = videoUrl;
        videoPreview.load();
      }
      if (downloadVideoBtn) {
        downloadVideoBtn.href = videoUrl;
        downloadVideoBtn.download = videoArtifact;
      }
    }

    if (receiptArtifact) {
      const receiptUrl = `/api/jobs/${job.id}/artifacts/${receiptArtifact}`;
      if (downloadReceiptBtn) {
        downloadReceiptBtn.href = receiptUrl;
        downloadReceiptBtn.download = receiptArtifact;
      }
    }

    if (outputPanel) outputPanel.style.display = "block";
  }

  // Fetch Jobs List
  async function fetchJobs() {
    if (!jobsListEl) return;

    try {
      const res = await fetch("/api/jobs");
      if (!res.ok) return;

      const jobs = await res.json();
      jobsListEl.innerHTML = "";

      if (jobs.length === 0) {
        jobsListEl.textContent = "Nessuna elaborazione recente nella cronologia.";
        if (clearHistoryBtn) clearHistoryBtn.style.display = "none";
        return;
      }

      if (clearHistoryBtn) clearHistoryBtn.style.display = "inline-block";

      jobs.forEach((j) => {
        const item = document.createElement("div");
        item.className = "job-item";

        const info = document.createElement("div");
        info.className = "job-item-info";

        const title = document.createElement("strong");
        title.textContent = `🎬 ${j.input_name} (${j.status})`;

        const details = document.createElement("small");
        details.textContent = `${j.created_at} - ${j.summary || "Elaborato"}`;

        info.appendChild(title);
        info.appendChild(details);
        item.appendChild(info);

        jobsListEl.appendChild(item);
      });
    } catch (err) {
      console.warn("Errore caricamento cronologia:", err);
    }
  }

  // Clear History
  async function clearHistory() {
    try {
      let res = await fetch("/api/jobs", { method: "DELETE" });
      if (res.status === 405) {
        res = await fetch("/api/jobs/clear", { method: "POST" });
      }

      if (!res.ok) throw new Error("Impossibile cancellare la cronologia");
      fetchJobs();
      if (outputPanel) outputPanel.style.display = "none";
      if (processStatusEl) {
        processStatusEl.textContent = "Cronologia eliminata (I video su disco rimangono salvati).";
        processStatusEl.className = "status-msg success";
      }
    } catch (err) {
      alert(`Errore: ${err.message}`);
    }
  }
})();
