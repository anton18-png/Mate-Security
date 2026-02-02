// Мобильное меню
const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const mobileMenu = document.getElementById('mobileMenu');

if (mobileMenuBtn && mobileMenu) {
  mobileMenuBtn.addEventListener('click', () => {
    mobileMenu.classList.toggle('active');
    mobileMenuBtn.innerHTML = mobileMenu.classList.contains('active') 
      ? '<i class="fas fa-times"></i>' 
      : '<i class="fas fa-bars"></i>';
  });
  
  // Закрытие меню при клике на ссылку
  document.querySelectorAll('.mobile-menu a').forEach(link => {
    link.addEventListener('click', () => {
      mobileMenu.classList.remove('active');
      mobileMenuBtn.innerHTML = '<i class="fas fa-bars"></i>';
    });
  });
}

// FAQ аккордеон
document.querySelectorAll('.faq-item').forEach(item => {
  const question = item.querySelector('.faq-question');
  const answer = item.querySelector('.faq-answer');
  const toggle = item.querySelector('.faq-toggle');
  
  question.addEventListener('click', () => {
    if (answer.classList.contains('open')) {
      answer.classList.remove('open');
      toggle.style.transform = 'rotate(0deg)';
    } else {
      // Закрываем другие открытые FAQ
      document.querySelectorAll('.faq-answer.open').forEach(openAnswer => {
        if (openAnswer !== answer) {
          openAnswer.classList.remove('open');
          openAnswer.previousElementSibling.querySelector('.faq-toggle').style.transform = 'rotate(0deg)';
        }
      });
      
      answer.classList.add('open');
      toggle.style.transform = 'rotate(45deg)';
    }
  });
});

// Ленивая загрузка изображений
const lazyImages = document.querySelectorAll('img[data-src]');

if ('IntersectionObserver' in window) {
  const imageObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const img = entry.target;
        img.src = img.dataset.src;
        img.removeAttribute('data-src');
        imageObserver.unobserve(img);
      }
    });
  });

  lazyImages.forEach(img => imageObserver.observe(img));
} else {
  // Fallback для старых браузеров
  lazyImages.forEach(img => {
    img.src = img.dataset.src;
    img.removeAttribute('data-src');
  });
}

// Плавная прокрутка
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function(e) {
    const href = this.getAttribute('href');
    if (href === '#' || href === '#!') return;
    
    e.preventDefault();
    const targetElement = document.querySelector(href);
    if (targetElement) {
      window.scrollTo({
        top: targetElement.offsetTop - 80,
        behavior: 'smooth'
      });
    }
  });
});

// Анимация при скролле
const animateOnScroll = () => {
  const elements = document.querySelectorAll('.card, .step, .screenshot-item');
  
  elements.forEach(el => {
    const elementTop = el.getBoundingClientRect().top;
    const elementVisible = 150;
    
    if (elementTop < window.innerHeight - elementVisible) {
      el.style.opacity = '1';
      el.style.transform = 'translateY(0)';
    }
  });
};

// Инициализация анимации
window.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.card, .step, .screenshot-item').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
  });
  
  // Первоначальный запуск анимации
  setTimeout(animateOnScroll, 100);
});

// Запуск анимации при скролле
window.addEventListener('scroll', animateOnScroll);