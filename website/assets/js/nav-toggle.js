document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("navToggle");
  const links = document.getElementById("navlinks");
  const closeMenu = () => {
    links?.classList.remove("is-open");
    toggle?.setAttribute("aria-expanded", "false");
  };
  toggle?.addEventListener("click", () => {
    const open = links?.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(Boolean(open)));
  });
  links
    ?.querySelectorAll("a")
    .forEach((link) => link.addEventListener("click", closeMenu));

  const trigger = document.getElementById("searchTrigger");
  const modal = document.getElementById("searchModal");
  const close = document.getElementById("searchClose");
  const box = document.getElementById("search");
  if (!trigger || !modal || !close || !box) return;
  let initialized = false;
  const openSearch = () => {
    closeMenu();
    modal.showModal();
    document.body.classList.add("search-open");
    if (!initialized && window.PagefindUI) {
      new window.PagefindUI({
        element: "#search",
        showSubResults: true,
        showImages: false,
      });
      initialized = true;
    } else if (!initialized) {
      box.textContent =
        "Search is available after npm run build and npm run preview.";
    }
    requestAnimationFrame(() => modal.querySelector("input")?.focus());
  };
  trigger.addEventListener("click", openSearch);
  close.addEventListener("click", () => modal.close());
  modal.addEventListener("click", (event) => {
    if (event.target === modal) modal.close();
  });
  modal.addEventListener("close", () =>
    document.body.classList.remove("search-open"),
  );
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenu();
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      if (!modal.open) openSearch();
    }
  });
});
