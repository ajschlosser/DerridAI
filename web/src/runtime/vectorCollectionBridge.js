/* Copyright 2026 Aaron John Schlosser, PhD. */

/** Live collection-creation bridge for the Vue Vector Stores workspace. */
export function createVectorCollectionBridge({
  state,
  workIndex,
  recordStores,
  tr,
  trf,
  esc,
  icon,
  api,
  refreshStores,
  persistPrefs,
  upsertRows,
  toast,
  openMessageModal,
  decorateDisabledControls,
  showAppModal,
}) {
  function notifyVectorStoresChanged() {
    window.dispatchEvent(new CustomEvent("derridai:vector-stores-changed"));
  }
  function openDatabaseCreationFromResearch() {
    state.vectorAutoCreateRequested = true;
    window.dispatchEvent(
      new CustomEvent("derridai:navigate-native", {
        detail: { path: "/databases", runtimeView: "vector" },
      }),
    );
  }

  function collectionSyncableWorks() {
    return [...workIndex().values()]
      .sort((a, b) => String(a.work).localeCompare(String(b.work)))
      .map((item) => ({ work: item.work, count: item.rows.length, rows: item.rows }));
  }

  function openCollectionCreationWizard({
    defaultProvider = "ollama",
    defaultModel = "bge-m3:latest",
    installedModels = [],
    providerProfiles = [],
  } = {}) {
    const dialog = document.createElement("dialog");
    dialog.className = "collection-wizard-dialog workflow-dialog collection-wizard-v037";
    const works = collectionSyncableWorks();
    const embeddingProfiles = (providerProfiles || []).filter(
      (profile) =>
        profile &&
        profile.id &&
        ["ollama", "openai"].includes(String(profile.type || "").toLowerCase()),
    );
    const requestedProvider = String(defaultProvider || "").toLowerCase();
    const profileDefault = embeddingProfiles.find(
      (profile) => String(profile.type || "").toLowerCase() === requestedProvider,
    );
    const initialProvider = String(defaultProvider || "").startsWith("profile:")
      ? String(defaultProvider)
      : ["chroma", "precomputed", "ollama"].includes(requestedProvider)
        ? requestedProvider
        : profileDefault
          ? `profile:${profileDefault.id}`
          : "chroma";
    const initialProfile = embeddingProfiles.find(
      (profile) => `profile:${profile.id}` === initialProvider,
    );
    const form = {
      name: recordStores().length ? "" : "derrida-primary",
      description: "",
      role: "primary",
      languages: new Set(),
      provider: initialProvider,
      model: String(initialProfile?.model || defaultModel || ""),
      dimension: "",
      distance: "cosine",
      retrieval: "hybrid",
      protected: false,
      selectedWorks: new Set(),
      preflight: null,
    };
    let step = 0;
    const steps = [
      tr("vector.create_step_source"),
      tr("vector.create_step_retrieval"),
      tr("vector.create_step_review"),
    ];
    const selectedRows = () =>
      works.filter((item) => form.selectedWorks.has(item.work)).flatMap((item) => item.rows);
    const selectedCount = () => selectedRows().length;
    const persistFields = () => {
      const name = dialog.querySelector("#wizardCollectionName");
      if (name) form.name = name.value.trim();
      const description = dialog.querySelector("#wizardCollectionDescription");
      if (description) form.description = description.value.trim();
      const role = dialog.querySelector("#wizardCollectionRole");
      if (role) form.role = role.value;
      const languageBoxes = [...dialog.querySelectorAll("[data-wizard-language]")];
      if (languageBoxes.length)
        form.languages = new Set(
          languageBoxes.filter((box) => box.checked).map((box) => box.dataset.wizardLanguage),
        );
      const provider = dialog.querySelector('input[name="wizardEmbeddingProviderRadio"]:checked');
      if (provider) form.provider = provider.value;
      const model = dialog.querySelector("#wizardEmbeddingModel");
      if (model) form.model = model.value.trim();
      const dimension = dialog.querySelector("#wizardEmbeddingDimension");
      if (dimension) form.dimension = dimension.value.trim();
      const distance = dialog.querySelector("#wizardDistanceMetric");
      if (distance) form.distance = distance.value;
      const retrieval = dialog.querySelector("#wizardRetrievalMode");
      if (retrieval) form.retrieval = retrieval.value;
      const protection = dialog.querySelector("#wizardProtected");
      if (protection) form.protected = protection.checked;
      const workBoxes = [...dialog.querySelectorAll("[data-wizard-work]")];
      if (workBoxes.length)
        form.selectedWorks = new Set(
          workBoxes.filter((box) => box.checked).map((box) => box.dataset.wizardWork),
        );
    };
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    const sourceStep = () => {
      const total = selectedCount();
      return `<section class="workflow-step-body"><div class="workflow-step-copy"><span class="section-label">${esc(tr("vector.create_collection"))}</span><h3>${esc(tr("vector.source_dataset"))}</h3><p>${esc(tr("vector.source_dataset_help"))}</p></div><div class="workflow-fields"><label class="field"><span>${esc(tr("vector.collection_name"))}</span><input class="control" id="wizardCollectionName" value="${esc(form.name)}" autocomplete="off" placeholder="derrida-primary"><small>${esc(tr("vector.collection_name_rules"))}</small></label><label class="field"><span>${esc(tr("vector.collection_description"))}</span><textarea class="control" id="wizardCollectionDescription" rows="2" placeholder="${esc(tr("vector.collection_description_placeholder"))}">${esc(form.description)}</textarea></label><div class="wizard-work-toolbar"><div><b>${esc(tr("vector.available_loaded_works"))}</b><small>${works.length ? trf("vector.available_works_count", { count: works.length.toLocaleString() }) : ""}</small></div>${works.length ? `<div class="tools"><button class="btn small" type="button" id="wizardSelectWorks">${esc(tr("ui.select_all"))}</button><button class="btn small" type="button" id="wizardClearWorks">${esc(tr("ui.clear"))}</button></div>` : ""}</div><div class="wizard-sync-summary"><span><b>${form.selectedWorks.size.toLocaleString()}</b>${esc(tr("dynamic.works"))}</span><span><b>${total.toLocaleString()}</b>${esc(tr("dynamic.records"))}</span></div><div class="wizard-work-list">${works.map((item) => `<label class="wizard-work-row"><input type="checkbox" data-wizard-work="${esc(item.work)}" ${form.selectedWorks.has(item.work) ? "checked" : ""}><span><b>${esc(item.work)}</b><small>${item.count.toLocaleString()} ${esc(tr("dynamic.records"))}</small></span></label>`).join("") || `<div class="empty-inline">${esc(tr("vector.no_loaded_works"))}</div>`}</div></div></section>`;
    };
    const retrievalStep = () =>
      `<section class="workflow-step-body"><div class="workflow-step-copy"><span class="section-label">${esc(tr("vector.create_collection"))}</span><h3>${esc(tr("vector.retrieval_contract"))}</h3><p>${esc(tr("vector.retrieval_contract_help"))}</p></div><div class="workflow-fields"><div class="wizard-two-col"><label class="field"><span>${esc(tr("vector.collection_role"))}</span><select class="control" id="wizardCollectionRole"><option value="primary" ${form.role === "primary" ? "selected" : ""}>${esc(tr("vector.role_primary"))}</option><option value="general" ${form.role === "general" ? "selected" : ""}>${esc(tr("vector.role_general"))}</option><option value="language" ${form.role === "language" ? "selected" : ""}>${esc(tr("vector.role_language"))}</option></select></label><fieldset class="vector-language-choice"><legend>${esc(tr("vector.language_tags"))}</legend><div class="vector-language-options">${[
        ["en", "English"],
        ["fr", "Français"],
      ]
        .map(
          ([code, name]) =>
            `<label><input type="checkbox" data-wizard-language="${code}" ${form.languages.has(code) ? "checked" : ""}><span>${name}</span></label>`,
        )
        .join(
          "",
        )}</div><small>${esc(tr("vector.language_tags_scope_help"))}</small></fieldset></div><fieldset class="vector-provider-choice"><legend>${esc(tr("vector.embedding_provider"))}</legend><div class="vector-provider-options">${[["ollama", tr("vector.provider_ollama"), tr("vector.provider_ollama_help")], ["chroma", tr("vector.provider_chroma"), tr("vector.provider_chroma_help")], ["precomputed", tr("vector.provider_precomputed"), tr("vector.provider_precomputed_help")], ...embeddingProfiles.map((profile) => [`profile:${profile.id}`, String(profile.name || profile.id), `${String(profile.type || "").toUpperCase()} · ${String(profile.model || tr("vector.embedding_model"))}`])].map(([value, name, help]) => `<label class="${form.provider === value ? "selected" : ""}"><input type="radio" name="wizardEmbeddingProviderRadio" value="${esc(value)}" ${form.provider === value ? "checked" : ""}><span><b>${esc(name)}</b><small>${esc(help)}</small></span></label>`).join("")}</div></fieldset><div class="wizard-two-col"><label class="field ${form.provider === "ollama" || form.provider.startsWith("profile:") ? "" : "muted-field"}"><span>${esc(tr("vector.embedding_model"))}</span><input class="control" id="wizardEmbeddingModel" list="wizardEmbeddingModels" value="${esc(form.model)}" ${form.provider === "ollama" || form.provider.startsWith("profile:") ? "" : "disabled"} placeholder="bge-m3:latest"><datalist id="wizardEmbeddingModels">${installedModels.map((model) => `<option value="${esc(model.name)}"></option>`).join("")}</datalist></label><label class="field"><span>${esc(tr("vector.embedding_dimension"))}</span><input class="control" id="wizardEmbeddingDimension" inputmode="numeric" value="${esc(form.dimension)}" placeholder="${form.provider === "precomputed" ? esc(tr("vector.dimension_optional")) : esc(tr("vector.dimension_auto"))}" ${form.provider === "precomputed" ? "" : "disabled"}><small>${esc(tr("vector.embedding_dimension_help"))}</small></label><label class="field"><span>${esc(tr("vector.distance_metric"))}</span><select class="control" id="wizardDistanceMetric"><option value="cosine" ${form.distance === "cosine" ? "selected" : ""}>Cosine</option><option value="l2" ${form.distance === "l2" ? "selected" : ""}>L2</option><option value="ip" ${form.distance === "ip" ? "selected" : ""}>Inner product</option></select></label><label class="field"><span>${esc(tr("vector.retrieval_mode"))}</span><select class="control" id="wizardRetrievalMode"><option value="hybrid" ${form.retrieval === "hybrid" ? "selected" : ""}>${esc(tr("vector.hybrid_recommended"))}</option><option value="semantic" ${form.retrieval === "semantic" ? "selected" : ""}>${esc(tr("vector.semantic_only"))}</option><option value="lexical" ${form.retrieval === "lexical" ? "selected" : ""}>${esc(tr("vector.lexical_only"))}</option></select><small>${esc(tr("vector.hybrid_help"))}</small></label></div><label class="vector-protection-toggle"><input type="checkbox" id="wizardProtected" ${form.protected ? "checked" : ""}><span><b>${esc(tr("vector.deletion_protection"))}</b><small>${esc(tr("vector.deletion_protection_help"))}</small></span></label></div></section>`;
    const reviewStep = () => {
      const total = selectedCount(),
        pf = form.preflight || {};
      const selectedProfile = embeddingProfiles.find(
        (profile) => `profile:${profile.id}` === form.provider,
      );
      const providerLabel = selectedProfile
        ? `${selectedProfile.name || selectedProfile.id} · ${form.model}`
        : form.provider === "ollama"
          ? `${tr("vector.provider_ollama")} · ${form.model}`
          : form.provider === "precomputed"
            ? tr("vector.provider_precomputed")
            : tr("vector.provider_chroma");
      return `<section class="workflow-step-body"><div class="workflow-step-copy"><span class="section-label">${esc(tr("vector.create_collection"))}</span><h3>${esc(tr("vector.review_build"))}</h3><p>${esc(tr("vector.review_build_help"))}</p></div><div class="workflow-fields"><div class="collection-preflight-card"><div class="collection-preflight-status ok">${icon("check")}<div><b>${esc(tr("vector.preflight_passed"))}</b><span>${esc(pf.message || tr("vector.preflight_ready"))}</span></div></div><dl class="manifest-review"><div><dt>${esc(tr("vector.collection"))}</dt><dd>${esc(form.name)}</dd></div><div><dt>${esc(tr("vector.source"))}</dt><dd>${form.selectedWorks.size.toLocaleString()} ${esc(tr("dynamic.works"))} · ${total.toLocaleString()} ${esc(tr("dynamic.records"))}</dd></div><div><dt>${esc(tr("vector.embedding_provider"))}</dt><dd>${esc(providerLabel)}</dd></div><div><dt>${esc(tr("vector.embedding_dimension"))}</dt><dd>${pf.embedding_dimension ?? (form.dimension || "—")}</dd></div><div><dt>${esc(tr("vector.distance_metric"))}</dt><dd>${esc(form.distance)}</dd></div><div><dt>${esc(tr("vector.retrieval_mode"))}</dt><dd>${esc(form.retrieval)}</dd></div><div><dt>${esc(tr("vector.query_embedding"))}</dt><dd>${pf.query_supported === false ? esc(tr("ui.no")) : esc(tr("ui.yes"))}</dd></div><div><dt>${esc(tr("vector.deletion_protection"))}</dt><dd>${form.protected ? esc(tr("ui.on")) : esc(tr("ui.off"))}</dd></div></dl>${total ? `<div class="info"><b>${esc(tr("vector.background_build"))}</b><span>${esc(trf("vector.background_build_help", { count: total.toLocaleString() }))}</span></div>` : `<div class="info"><span>${esc(tr("vector.empty_manifest_help"))}</span></div>`}</div></div></section>`;
    };
    const stepContent = () =>
      step === 0 ? sourceStep() : step === 1 ? retrievalStep() : reviewStep();
    const runPreflight = async (button) => {
      persistFields();
      if ((form.provider === "ollama" || form.provider.startsWith("profile:")) && !form.model) {
        toast(tr("vector.embedding_model_required"));
        return false;
      }
      button.disabled = true;
      const old = button.innerHTML;
      button.textContent = tr("vector.running_preflight");
      try {
        form.preflight = await api("/api/stores/preflight/embedding", {
          method: "POST",
          body: JSON.stringify({
            embedding_provider: form.provider,
            embedding_model:
              form.provider === "ollama" || form.provider.startsWith("profile:")
                ? form.model
                : null,
            embedding_dimension: form.dimension ? Number(form.dimension) : null,
            distance_metric: form.distance,
          }),
        });
        if (form.preflight?.embedding_dimension)
          form.dimension = String(form.preflight.embedding_dimension);
        return true;
      } catch (error) {
        openMessageModal({
          title: tr("vector.preflight_failed"),
          message: error.message || String(error),
          tone: "danger",
        });
        return false;
      } finally {
        button.disabled = false;
        button.innerHTML = old;
      }
    };
    const render = () => {
      dialog.innerHTML = `<div class="workflow-dialog-head"><div><span class="section-label">${esc(tr("vector.new_collection"))}</span><h2>${esc(tr("vector.new_direction_build"))}</h2><p>${esc(tr("vector.new_direction_build_help"))}</p></div><button class="btn icon-only" type="button" data-close aria-label="${esc(tr("ui.close"))}">${icon("close")}</button></div><ol class="workflow-steps" aria-label="${esc(tr("vector.creation_steps"))}">${steps.map((label, index) => `<li class="${index === step ? "active" : index < step ? "done" : ""}"><span>${index + 1}</span><b>${esc(label)}</b></li>`).join("")}</ol>${stepContent()}<div class="workflow-dialog-actions"><button class="btn" type="button" data-close>${esc(tr("ui.cancel"))}</button><div class="workflow-action-spacer"></div>${step ? `<button class="btn" type="button" id="wizardBack">← ${esc(tr("ui.back"))}</button>` : ""}${step < 2 ? `<button class="btn primary" type="button" id="wizardNext">${esc(step === 1 ? tr("vector.preflight_and_review") : tr("ui.next"))} →</button>` : `<button class="btn primary" type="button" id="wizardCreate">${icon("plus")}${esc(form.selectedWorks.size ? tr("vector.create_and_build") : tr("vector.create_empty"))}</button>`}</div>`;
      dialog.querySelectorAll("[data-close]").forEach((button) => (button.onclick = close));
      dialog.querySelector("#wizardBack")?.addEventListener("click", () => {
        persistFields();
        step = Math.max(0, step - 1);
        render();
      });
      dialog.querySelector("#wizardNext")?.addEventListener("click", async (event) => {
        persistFields();
        if (step === 0 && !form.name) return toast(tr("vector.collection_name_required"));
        if (step === 0) {
          step = 1;
          render();
          return;
        }
        if (step === 1) {
          const ok = await runPreflight(event.currentTarget);
          if (ok) {
            step = 2;
            render();
          }
        }
      });
      dialog.querySelectorAll('input[name="wizardEmbeddingProviderRadio"]').forEach((input) =>
        input.addEventListener("change", (event) => {
          persistFields();
          form.provider = event.target.value;
          const profile = embeddingProfiles.find((item) => `profile:${item.id}` === form.provider);
          if (profile?.model) form.model = String(profile.model);
          else if (form.provider === "ollama" && !form.model)
            form.model = String(defaultModel || "");
          form.preflight = null;
          render();
        }),
      );
      dialog.querySelector("#wizardSelectWorks")?.addEventListener("click", () => {
        persistFields();
        form.selectedWorks = new Set(works.map((item) => item.work));
        render();
      });
      dialog.querySelector("#wizardClearWorks")?.addEventListener("click", () => {
        persistFields();
        form.selectedWorks.clear();
        render();
      });
      dialog.querySelectorAll("[data-wizard-work]").forEach((input) =>
        input.addEventListener("change", () => {
          persistFields();
          render();
        }),
      );
      dialog.querySelector("#wizardCreate")?.addEventListener("click", async () => {
        persistFields();
        if (!form.name) return toast(tr("vector.collection_name_required"));
        const button = dialog.querySelector("#wizardCreate");
        button.disabled = true;
        button.textContent = tr("vector.creating_collection");
        try {
          await api("/api/stores", {
            method: "POST",
            body: JSON.stringify({
              name: form.name,
              description: form.description || null,
              embedding_provider: form.provider,
              embedding_model:
                form.provider === "ollama" || form.provider.startsWith("profile:")
                  ? form.model
                  : null,
              embedding_dimension: form.dimension ? Number(form.dimension) : null,
              distance_metric: form.distance,
              retrieval_mode: form.retrieval,
              text_field: "text",
              language_codes: form.languages.size ? [...form.languages] : null,
              collection_role: form.role || null,
              protected: form.protected,
            }),
          });
          await refreshStores();
          state.activeStore = form.name;
          state.storePage = 1;
          state.storeSearchResults = [];
          state.storeWork = "";
          state.storeWorksStore = "";
          state.storeBrowseMode = "works";
          persistPrefs();
          const rows = selectedRows();
          close();
          const syncStarted = rows.length
            ? await upsertRows(
                rows,
                trf("vector.selected_works_label", { count: form.selectedWorks.size }),
                { largeSyncConfirmed: true },
              )
            : false;
          toast(
            rows.length && syncStarted
              ? trf("vector.collection_created_build", { name: form.name })
              : trf("vector.collection_created", { name: form.name }),
            { tone: "success" },
          );
          notifyVectorStoresChanged();
        } catch (error) {
          button.disabled = false;
          button.textContent = tr("vector.create_collection");
          openMessageModal({
            title: tr("vector.create_failed"),
            message: error.message || String(error),
            tone: "danger",
          });
        }
      });
      decorateDisabledControls(dialog);
    };
    document.body.appendChild(dialog);
    render();
    showAppModal(dialog);
  }

  return {
    notifyVectorStoresChanged,
    openDatabaseCreationFromResearch,
    openCollectionCreationWizard,
  };
}
