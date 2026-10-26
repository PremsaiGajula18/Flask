// Trip Planner interactive JS
document.addEventListener('DOMContentLoaded', () => {
  // Flash messages auto-dismiss or manual dismiss
  const flashMessages = document.querySelectorAll('.flash-message');
  flashMessages.forEach((msg) => {
    const closeBtn = msg.querySelector('.flash-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        msg.style.opacity = '0';
        msg.style.transform = 'translateY(-10px)';
        setTimeout(() => msg.remove(), 250);
      });
    }

    // Auto-dismiss after 6 seconds
    setTimeout(() => {
      if (msg && msg.parentElement) {
        msg.style.opacity = '0';
        msg.style.transform = 'translateY(-10px)';
        setTimeout(() => msg.remove(), 250);
      }
    }, 6000);
  });

  // Client-side validation enhancement for trip forms
  const tripForm = document.querySelector('#tripForm');
  if (tripForm) {
    const startDateInput = tripForm.querySelector('#start_date');
    const endDateInput = tripForm.querySelector('#end_date');
    const budgetInput = tripForm.querySelector('#budget');

    tripForm.addEventListener('submit', (e) => {
      let hasError = false;

      // Validate dates
      if (startDateInput && endDateInput && startDateInput.value && endDateInput.value) {
        if (new Date(endDateInput.value) < new Date(startDateInput.value)) {
          alert('End date cannot be earlier than start date.');
          endDateInput.focus();
          e.preventDefault();
          return;
        }
      }

      // Validate budget
      if (budgetInput && budgetInput.value) {
        if (parseFloat(budgetInput.value) < 0) {
          alert('Budget cannot be negative.');
          budgetInput.focus();
          e.preventDefault();
          return;
        }
      }
    });

    if (startDateInput && endDateInput) {
      startDateInput.addEventListener('change', () => {
        if (startDateInput.value) {
          endDateInput.min = startDateInput.value;
        }
      });
    }
  }

  // Client-side validation for activity forms
  const activityForm = document.querySelector('#activityForm');
  if (activityForm) {
    const costInput = activityForm.querySelector('#cost');
    activityForm.addEventListener('submit', (e) => {
      if (costInput && costInput.value) {
        if (parseFloat(costInput.value) < 0) {
          alert('Activity cost cannot be negative.');
          costInput.focus();
          e.preventDefault();
          return;
        }
      }
    });
  }
});
