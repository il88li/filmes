(function() {
    'use strict';

    // ============================================================
    // 1. PORTFOLIO — جلب البيانات من API وعرضها مع فلترة
    // ============================================================
    const grid = document.getElementById('portfolioGrid');
    const filterBtns = document.querySelectorAll('.filter-btn');
    let currentFilter = 'all';
    let allProjects = [];

    // دالة العرض
    function renderPortfolio(filter) {
        const filtered = filter === 'all' ?
            allProjects :
            allProjects.filter(item => item.category === filter);

        if (filtered.length === 0) {
            grid.innerHTML = `<p style="text-align:center; grid-column:1/-1; color:var(--color-text-muted);">
                لا توجد أعمال في هذه الفئة حالياً.
            </p>`;
            return;
        }

        grid.innerHTML = filtered.map(item => {
            const imgHtml = item.image_url ?
                `<img src="${item.image_url}" alt="${item.title}" loading="lazy" />` :
                `<div class="placeholder"><i class="fas fa-image"></i></div>`;
            return `
                <div class="portfolio-item" data-category="${item.category}">
                    ${imgHtml}
                    <div class="overlay-label">${item.title}</div>
                </div>
            `;
        }).join('');
    }

    // جلب البيانات من الخادم
    async function fetchProjects() {
        try {
            const response = await fetch('/api/projects');
            if (!response.ok) throw new Error('فشل جلب البيانات');
            allProjects = await response.json();
            renderPortfolio(currentFilter);
        } catch (error) {
            console.error(error);
            grid.innerHTML = `<p style="text-align:center; grid-column:1/-1; color:#ff6b6b;">
                <i class="fas fa-exclamation-triangle"></i> حدث خطأ في تحميل الأعمال. يرجى تحديث الصفحة.
            </p>`;
        }
    }

    // أحداث أزرار الفلترة
    filterBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            filterBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentFilter = this.dataset.filter;
            renderPortfolio(currentFilter);
        });
    });

    // تشغيل الجلب عند تحميل الصفحة
    document.addEventListener('DOMContentLoaded', fetchProjects);

    // ============================================================
    // 2. TESTIMONIALS SLIDER
    // ============================================================
    const track = document.getElementById('testimonialTrack');
    const prevBtn = document.getElementById('prevTestimonial');
    const nextBtn = document.getElementById('nextTestimonial');
    let currentSlide = 0;
    const slides = track.querySelectorAll('.testimonial');
    const totalSlides = slides.length;

    function goToSlide(index) {
        if (index < 0) index = totalSlides - 1;
        if (index >= totalSlides) index = 0;
        currentSlide = index;
        track.style.transform = 'translateX(-' + (currentSlide * 100) + '%)';
    }

    prevBtn.addEventListener('click', function() { goToSlide(currentSlide - 1); });
    nextBtn.addEventListener('click', function() { goToSlide(currentSlide + 1); });

    let autoSlide = setInterval(function() { goToSlide(currentSlide + 1); }, 5000);
    const sliderContainer = document.querySelector('.testimonials-slider');
    sliderContainer.addEventListener('mouseenter', function() { clearInterval(autoSlide); });
    sliderContainer.addEventListener('mouseleave', function() {
        autoSlide = setInterval(function() { goToSlide(currentSlide + 1); }, 5000);
    });

    // ============================================================
    // 3. STATS — عداد متحرك
    // ============================================================
    const statNumbers = document.querySelectorAll('.stat-card .number');
    let statsAnimated = false;

    function animateStats() {
        if (statsAnimated) return;
        const triggerPoint = window.innerHeight * 0.85;
        const statsSection = document.getElementById('stats');
        const rect = statsSection.getBoundingClientRect();
        if (rect.top < triggerPoint) {
            statsAnimated = true;
            statNumbers.forEach(el => {
                const target = parseInt(el.dataset.count, 10);
                let current = 0;
                const increment = Math.ceil(target / 40);
                const timer = setInterval(function() {
                    current += increment;
                    if (current >= target) {
                        current = target;
                        clearInterval(timer);
                    }
                    el.textContent = current + (el.dataset.count === '60' ? '%' : '');
                }, 30);
            });
        }
    }

    window.addEventListener('scroll', animateStats);
    window.addEventListener('load', function() { setTimeout(animateStats, 300); });

    // ============================================================
    // 4. FADE-UP EFFECT
    // ============================================================
    document.querySelectorAll('.section-title, .service-card, .tool-item, .stat-card, .social-link')
        .forEach(el => { if (!el.classList.contains('fade-up')) el.classList.add('fade-up'); });

    function handleFade() {
        const trigger = window.innerHeight * 0.88;
        document.querySelectorAll('.fade-up:not(.visible)').forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.top < trigger) {
                el.classList.add('visible');
            }
        });
    }

    window.addEventListener('scroll', handleFade);
    window.addEventListener('load', function() { setTimeout(handleFade, 200); });

})();