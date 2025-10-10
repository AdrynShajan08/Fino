// voice_input.js

const startVoiceBtn = document.getElementById("startVoiceBtn");
const voiceText = document.getElementById("voiceText");

let recognition;

if ("webkitSpeechRecognition" in window) {
  recognition = new webkitSpeechRecognition();
  recognition.continuous = false;
  recognition.lang = "en-IN";
  recognition.interimResults = false;
} else {
  alert("Your browser does not support speech recognition.");
}

if (startVoiceBtn && recognition) {
  startVoiceBtn.addEventListener("click", () => {
    recognition.start();
    voiceText.textContent = "Listening...";
  });

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    voiceText.textContent = `Heard: "${transcript}"`;
    parseVoiceInput(transcript);
  };

  recognition.onerror = (e) => {
    voiceText.textContent = "Error capturing voice. Try again.";
    console.error(e);
  };
}

function parseVoiceInput(text) {
  // Example: "Spent 500 on groceries today"
  const regex = /spent\s+(\d+(?:\.\d+)?)\s+(?:on\s+)?(\w+)/i;
  const match = text.match(regex);

  if (match) {
    const amount = match[1];
    const category = match[2].toLowerCase();
    document.getElementById("amount").value = amount;

    // Try to match the category from the dropdown
    const categorySelect = document.getElementById("category");
    const options = Array.from(categorySelect.options);
    const matchedOption = options.find(opt => category.includes(opt.value));

    if (matchedOption) {
      categorySelect.value = matchedOption.value;
    } else {
      categorySelect.value = "other";
    }

    document.getElementById("description").value = text;
  } else {
    voiceText.textContent = "Couldn't detect amount or category. Try again.";
  }
}
