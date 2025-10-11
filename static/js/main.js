const expenseForm = document.getElementById("expenseForm");
const messageDiv = document.getElementById("message");

if (expenseForm) {
  expenseForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const expenseData = {
      amount: document.getElementById("amount").value,
      category: document.getElementById("category").value,
      description: document.getElementById("description").value
    };

    try {
      const response = await fetch("/add_expense", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(expenseData)
      });

      const result = await response.json();
      messageDiv.textContent = result.message;
      messageDiv.style.color = "green";

      expenseForm.reset();
    } catch (error) {
      console.error(error);
      messageDiv.textContent = "Failed to add expense.";
      messageDiv.style.color = "red";
    }
  });
}
