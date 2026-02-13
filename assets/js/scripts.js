// ===== Pantry Storage Helpers =====
function loadPantry() {
  // Load from localStorage or return empty array
  try {
    return JSON.parse(localStorage.getItem("pantry")) || [];
  } catch (e) {
    console.error("Error loading pantry from localStorage:", e);
    return [];
  }
}

function savePantry(items) {
  try {
    localStorage.setItem("pantry", JSON.stringify(items));
  } catch (e) {
    console.error("Error saving pantry to localStorage:", e);
  }
}

// ===== Default Pantry Items =====
const DEFAULT_PANTRY = [
  "salt", "black pepper", "olive oil", "garlic", "onion",
  "butter", "eggs", "milk", "rice", "pasta"
];

let selected = new Set(); // will populate on DOMContentLoaded

// ===== Render Pantry List =====
function renderList() {
  const ul = document.getElementById("ingredientsList");
  if (!ul) return; // in case DOM not ready

  ul.innerHTML = "";

  DEFAULT_PANTRY.forEach(item => {
    const li = document.createElement("li");

    // emoji icon
    const icon = document.createElement("span");
    icon.textContent = "🥘";
    icon.style.opacity = "0.9";
    icon.style.marginRight = "6px";

    const text = document.createElement("span");
    text.textContent = item.charAt(0).toUpperCase() + item.slice(1);

    li.appendChild(icon);
    li.appendChild(text);

    if (selected.has(item)) li.classList.add("selected");

    li.onclick = () => {
      selected.has(item) ? selected.delete(item) : selected.add(item);
      renderList();
    };

    ul.appendChild(li);
  });
}

// ===== Add Custom Item =====
function addCustomItem() {
  const input = document.getElementById("customItem");
  if (!input) return;

  const val = input.value.trim().toLowerCase();
  if (!val) return;

  selected.add(val);
  input.value = "";
  renderList();
}

// ===== Confirm Pantry =====
function confirmPantry() {
  savePantry(Array.from(selected));
  window.location.href = "video-analysis.html";
}

// ===== Initialize on DOM Ready =====
document.addEventListener("DOMContentLoaded", () => {
  // Load saved pantry or default
  const saved = loadPantry();
  if (saved.length > 0) {
    selected = new Set(saved);
  } else {
    selected = new Set(DEFAULT_PANTRY);
  }

  renderList();

  // Attach button handlers
  const addBtn = document.querySelector("button[onclick='addCustomItem()']");
  const confirmBtn = document.querySelector("button[onclick='confirmPantry()']");

  if (addBtn) addBtn.addEventListener("click", addCustomItem);
  if (confirmBtn) confirmBtn.addEventListener("click", confirmPantry);
});
