/* ==========================================================================
   Recruitify ATS — Multi-Page Interactive Controller
   Handles Mobile Navigation, Video Modals, Pricing Switcher, FAQs, & Kanban
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Mobile Navigation Toggle
  const mobileToggle = document.getElementById('mobileToggle');
  const mobileNavDrawer = document.getElementById('mobileNavDrawer');

  if (mobileToggle && mobileNavDrawer) {
    mobileToggle.addEventListener('click', () => {
      mobileNavDrawer.classList.toggle('active');
      const icon = mobileToggle.querySelector('i');
      if (icon) {
        if (mobileNavDrawer.classList.contains('active')) {
          icon.classList.remove('fa-bars');
          icon.classList.add('fa-xmark');
        } else {
          icon.classList.remove('fa-xmark');
          icon.classList.add('fa-bars');
        }
      }
    });
  }

  // 2. Pricing Billing Toggle (Monthly / Annual)
  const billingSwitch = document.getElementById('billingSwitch');
  const priceAmounts = document.querySelectorAll('.pricing-amount');

  if (billingSwitch && priceAmounts.length > 0) {
    billingSwitch.addEventListener('change', (e) => {
      const isAnnual = e.target.checked;
      priceAmounts.forEach(el => {
        const monthlyPrice = el.getAttribute('data-monthly');
        const annualPrice = el.getAttribute('data-annual');
        
        if (isAnnual && annualPrice) {
          el.innerHTML = `$${annualPrice} <span>/month billed annually</span>`;
        } else if (monthlyPrice) {
          el.innerHTML = `$${monthlyPrice} <span>/month</span>`;
        }
      });
    });
  }

  // 3. FAQ Accordion Toggle
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach(item => {
    const question = item.querySelector('.faq-question');
    if (question) {
      question.addEventListener('click', () => {
        const isActive = item.classList.contains('active');
        // Close other FAQs
        faqItems.forEach(i => i.classList.remove('active'));
        if (!isActive) {
          item.classList.add('active');
        }
      });
    }
  });

  // 4. Video Showcase Play Button / Modal
  const playVideoBtn = document.getElementById('playVideoBtn');
  const videoModal = document.getElementById('videoModal');
  const closeVideoModal = document.getElementById('closeVideoModal');
  const modalVideoPlayer = document.getElementById('modalVideoPlayer');

  if (playVideoBtn && videoModal) {
    playVideoBtn.addEventListener('click', (e) => {
      e.preventDefault();
      videoModal.style.display = 'flex';
      if (modalVideoPlayer) {
        modalVideoPlayer.play().catch(() => {});
      }
    });
  }

  if (closeVideoModal && videoModal) {
    closeVideoModal.addEventListener('click', () => {
      videoModal.style.display = 'none';
      if (modalVideoPlayer) {
        modalVideoPlayer.pause();
      }
    });

    videoModal.addEventListener('click', (e) => {
      if (e.target === videoModal) {
        videoModal.style.display = 'none';
        if (modalVideoPlayer) {
          modalVideoPlayer.pause();
        }
      }
    });
  }

  // 5. Interactive Demo Kanban Card Drag & Drop Simulation
  const kanbanCards = document.querySelectorAll('.kanban-card');
  const kanbanColumns = document.querySelectorAll('.kanban-column');

  kanbanCards.forEach(card => {
    card.setAttribute('draggable', 'true');
    card.addEventListener('dragstart', (e) => {
      card.classList.add('dragging');
      e.dataTransfer.setData('text/plain', card.id);
    });

    card.addEventListener('dragend', () => {
      card.classList.remove('dragging');
    });
  });

  kanbanColumns.forEach(col => {
    col.addEventListener('dragover', (e) => {
      e.preventDefault();
      col.classList.add('drag-over');
    });

    col.addEventListener('dragleave', () => {
      col.classList.remove('drag-over');
    });

    col.addEventListener('drop', (e) => {
      e.preventDefault();
      col.classList.remove('drag-over');
      const draggingCard = document.querySelector('.kanban-card.dragging');
      if (draggingCard) {
        col.appendChild(draggingCard);
        updateKanbanCounts();
        showToast('Candidate pipeline stage updated successfully!', 'success');
      }
    });
  });

  function updateKanbanCounts() {
    kanbanColumns.forEach(col => {
      const countPill = col.querySelector('.kanban-count-pill');
      const cardCount = col.querySelectorAll('.kanban-card').length;
      if (countPill) {
        countPill.textContent = cardCount;
      }
    });
  }

  // 6. Global Toast Notification System
  window.showToast = function(message, type = 'info') {
    let container = document.getElementById('toastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toastContainer';
      container.style.cssText = 'position: fixed; bottom: 24px; right: 24px; z-index: 9999; display: flex; flex-direction: column; gap: 10px;';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bgColor = type === 'success' ? '#00e676' : type === 'warning' ? '#f59e0b' : '#043442';
    const textColor = type === 'success' ? '#02222c' : '#ffffff';

    toast.style.cssText = `background: ${bgColor}; color: ${textColor}; padding: 12px 20px; border-radius: 8px; font-weight: 700; font-size: 0.9rem; box-shadow: 0 10px 25px rgba(0,0,0,0.2); opacity: 0; transform: translateY(10px); transition: all 0.3s ease; display: flex; align-items: center; gap: 8px;`;
    toast.innerHTML = `<i class="fa-solid ${type === 'success' ? 'fa-check-circle' : 'fa-info-circle'}"></i> ${message}`;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '1';
      toast.style.transform = 'translateY(0)';
    }, 10);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  };
});
