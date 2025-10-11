const voiceBtn = document.getElementById("voiceBtn");
const form = document.getElementById("expenseForm");

if ("webkitSpeechRecognition" in window) {
  const recognition = new webkitSpeechRecognition();
  recognition.continuous = false;
  recognition.lang = "en-IN";

  voiceBtn.addEventListener("click", () => {
    document.getElementById("status").innerText = "🎧 Listening...";
    recognition.start();
  });

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript.toLowerCase();
    document.getElementById("status").innerText = "🎙️ Recognized: " + transcript;

    // Extract amount
    const amountMatch = transcript.match(/(\d+(\.\d+)?)/);
    if (amountMatch) form.amount.value = amountMatch[1];

    // Extract category
    const categories = [
      "utilities", "rent", "dining", "turf", "entertainment",
      "charity", "groceries", "shopping"
    ];
    const foundCat = categories.find(cat => transcript.includes(cat));
    form.category.value = foundCat || "other";

    // Description = full text
    form.description.value = transcript;
  };

  recognition.onerror = (event) => {
    document.getElementById("status").innerText = "❌ Voice error: " + event.error;
  };
} else {
  voiceBtn.style.display = "none";
  document.getElementById("status").innerText = "Voice input not supported on this browser.";
}
