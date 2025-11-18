(function () {
  const trackSelect = document.querySelector('select[name="track"]');
  const levelSelect = document.querySelector("#filterLevel");

  if (trackSelect && levelSelect) {
    const updateLevels = () => {
      const track = trackSelect.value || "";
      const options = Array.from(levelSelect.options);
      options.forEach((opt, idx) => {
        if (idx === 0 && opt.value === "") {
          opt.hidden = false;
          opt.disabled = false;
          return;
        }
        const program = opt.dataset.program || "";
        const match = !track || program === track;
        opt.hidden = !match;
        opt.disabled = !match;
      });

      levelSelect.disabled = !track;
      if (!track) {
        levelSelect.value = "";
      } else {
        const current = options.find(
          (opt) => opt.value === levelSelect.value && !opt.disabled
        );
        if (!current) {
          const firstVisible = options.find(
            (opt, idx) => idx > 0 && !opt.disabled
          );
          levelSelect.value = firstVisible ? firstVisible.value : "";
        }
      }
    };

    trackSelect.addEventListener("change", updateLevels);
    updateLevels();
  }
})();

(function () {
  const modalEl = document.getElementById("deleteStudentModal");
  const form = document.getElementById("deleteStudentForm");
  const nameEl = document.getElementById("deleteStudentName");
  const deleteButtons = document.querySelectorAll(".js-delete-student");

  if (!modalEl || !form || !nameEl || !deleteButtons.length || !window.bootstrap) return;

  const modal = new bootstrap.Modal(modalEl);

  deleteButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const url = btn.dataset.deleteUrl;
      const name = btn.dataset.studentName || "học viên";
      form.action = url;
      nameEl.textContent = name;
      modal.show();
    });
  });
})();

(function () {
  const alertContainer = document.getElementById("alertMessages");
  if (!alertContainer) return;

  const dismissButtons = alertContainer.querySelectorAll(".js-alert-dismiss");
  dismissButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const alert = btn.closest(".alert");
      if (alert) alert.remove();
    });
  });

  setTimeout(() => {
    alertContainer.querySelectorAll(".alert").forEach((alert) => alert.remove());
  }, 10000);
})();

(function () {
  const modalEl = document.getElementById("viewStudentModal");
  const nameEl = document.getElementById("viewStudentName");
  const phoneEl = document.getElementById("viewStudentPhone");
  const emailEl = document.getElementById("viewStudentEmail");
  const programEl = document.getElementById("viewStudentProgram");
  const levelEl = document.getElementById("viewStudentLevel");
  const classEl = document.getElementById("viewStudentClass");
  const coursesEl = document.getElementById("viewStudentCourses");
  const primaryEl = document.getElementById("viewStudentPrimary");
  const addressEl = document.getElementById("viewStudentAddress");
  const statusEl = document.getElementById("viewStudentStatus");
  const enrollEl = document.getElementById("viewStudentEnroll");
  const financeEl = document.getElementById("viewStudentFinance");
  const createdEl = document.getElementById("viewStudentCreated");
  const updatedEl = document.getElementById("viewStudentUpdated");
  const notesEl = document.getElementById("viewStudentNotes");
  const editBtn = document.getElementById("viewStudentEdit");
  const deleteBtn = document.getElementById("viewStudentDelete");

  const buttons = document.querySelectorAll(".js-view-student");
  if (!modalEl || !buttons.length || !window.bootstrap) return;

  let modal = null;

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      if (!modal) modal = new bootstrap.Modal(modalEl);
      nameEl.textContent = btn.dataset.studentName || "N/A";
      phoneEl.textContent = btn.dataset.studentPhone || "—";
      emailEl.textContent = btn.dataset.studentEmail || "—";
      addressEl.textContent = btn.dataset.studentAddress || "—";
      programEl.textContent = btn.dataset.studentProgram || "—";
      levelEl.textContent = btn.dataset.studentLevel || "—";
      classEl.textContent = btn.dataset.studentClass || "—";
      primaryEl.textContent = btn.dataset.studentPrimary || "—";
      coursesEl.textContent = btn.dataset.studentCourses || "—";
      statusEl.textContent = btn.dataset.studentStatus || "—";
      enrollEl.textContent = btn.dataset.studentEnroll || "—";
      financeEl.textContent = btn.dataset.studentFinance || "—";
      createdEl.textContent = btn.dataset.studentCreated || "—";
      updatedEl.textContent = btn.dataset.studentUpdated || "—";
      notesEl.textContent = btn.dataset.studentNotes || "—";

      const editUrl = btn.dataset.studentEdit || "#";
      const deleteUrl = btn.dataset.studentDelete || btn.dataset.deleteUrl || "#";
      if (editBtn) {
        editBtn.onclick = () => {
          if (editUrl && editUrl !== "#") window.location.href = editUrl;
        };
      }
      if (deleteBtn) {
        deleteBtn.onclick = () => {
          modal.hide();
          const deleteTrigger = document.querySelector(
            `.js-delete-student[data-delete-url='${deleteUrl}']`
          );
          if (deleteTrigger) deleteTrigger.click();
        };
      }
      modal.show();
    });
  });
})();
