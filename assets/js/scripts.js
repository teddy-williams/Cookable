// ================= Pantry Utilities =================
function savePantry(pantry) {
  localStorage.setItem("pantry", JSON.stringify(pantry));
}

function loadPantry() {
  return JSON.parse(localStorage.getItem("pantry")) || [];
}

// ================= Settings Utilities =================
function saveSettings(settings) {
  localStorage.setItem("settings", JSON.stringify(settings));
}

function loadSettings() {
  return JSON.parse(localStorage.getItem("settings")) || {};
}

// ================= Clipboard Helper =================
function copyToClipboard(text) {
  navigator.clipboard.writeText(text);
  alert("Copied to clipboard!");
}

// ================= Pantry UI Functions =================
function renderPantryList(listElementId, defaultItems, selectedSet) {
  const ul = document.getElementById(listElementId);
  ul.innerHTML = "";

  defaultItems.forEach(item => {
    const li = document.createElement("li");

    // Optional: small food icon
    const icon = document.createElement("img");
    icon.src = "../assets/images/pantry.svg"; // replace with specific icons if you like
    icon.alt = "";

    li.appendChild(icon);
    li.appendChild(document.createTextNode(item));

    if (selectedSet.has(item)) li.classList.add("selected");

    li.onclick = () => {
      selectedSet.has(item) ? selectedSet.delete(item) : selectedSet.add(item);
      renderPantryList(listElementId, defaultItems, selectedSet);
    }

    ul.appendChild(li);
  });
}

function addCustomPantryItem(inputId, selectedSet, listElementId, defaultItems) {
  const input = document.getElementById(inputId);
  const val = input.value.trim();
  if(val) { 
    selectedSet.add(val); 
    input.value = ""; 
    renderPantryList(listElementId, defaultItems, selectedSet); 
  }
}

// ================= Video Analysis Functions =================
async function analyzeVideo(videoUrl, pantry) {
  if(!pantry.length) { 
    alert("Please select your pantry first."); 
    window.location.href="index.html"; 
    return; 
  }

  const res = await fetch("/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ video_url: videoUrl, pantry })
  });

  const data = await res.json();
  const parsed = data.result || data;
  return parsed;
}

function displayAnalysisResult(parsed) {
  document.getElementById("dishName").textContent = parsed.dish_name || "Recipe";
  document.getElementById("confidence").textContent = "Confidence: " + (parsed.confidence||"unknown");
  fillList("haveList", parsed.have || []);
  fillList("buyList", parsed.need_to_buy || []);
  document.getElementById("result").style.display = "block";
}

function fillList(id, items) {
  const ul = document.getElementById(id);
  ul.innerHTML = "";
  items.forEach(item => {
    const li = document.createElement("li");
    li.textContent = item;
    ul.appendChild(li);
  });
}

function copyShoppingList() {
  const items = [...document.querySelectorAll("#buyList li")].map(li=>"- "+li.textContent).join("\n");
  copyToClipboard(items);
}
