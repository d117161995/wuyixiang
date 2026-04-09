// 数字动画
function animateNumber(element, target, suffix = '') {
    const duration = 2000;
    const start = 0;
    const increment = target / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            element.textContent = target + suffix;
            clearInterval(timer);
        } else {
            element.textContent = Math.floor(current) + suffix;
        }
    }, 16);
}

// 统计数字动画观察器
const statObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting && !entry.target.classList.contains('animated')) {
            const target = parseInt(entry.target.getAttribute('data-target'));
            const suffix = entry.target.textContent.includes('%') ? '%' : '';
            animateNumber(entry.target, target, suffix);
            entry.target.classList.add('animated');
        }
    });
}, { threshold: 0.5 });

document.querySelectorAll('.stat-value').forEach(stat => {
    statObserver.observe(stat);
});

// 导航栏滚动效果
let lastScroll = 0;
const navbar = document.getElementById('navbar');

window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;
    if (currentScroll > 100) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
    lastScroll = currentScroll;
});

// 平滑滚动
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const targetId = this.getAttribute('href');
        const target = document.querySelector(targetId);
        if (target) {
            const offsetTop = target.offsetTop - 80;
            window.scrollTo({
                top: offsetTop,
                behavior: 'smooth'
            });
        }
    });
});


        // 主题卡片动画
        const cardObserverOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const cardObserver = new IntersectionObserver((entries) => {
            entries.forEach((entry, index) => {
                if (entry.isIntersecting) {
                    setTimeout(() => {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                        entry.target.classList.add('visible');
                    }, index * 100);
                }
            });
        }, cardObserverOptions);

document.querySelectorAll('.theme-card').forEach(card => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(30px)';
    card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    cardObserver.observe(card);
});

// 特点卡片动画
const featureObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry, index) => {
        if (entry.isIntersecting) {
            setTimeout(() => {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }, index * 100);
        }
    });
}, { threshold: 0.2 });

document.querySelectorAll('.feature-card').forEach(card => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px)';
    card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    featureObserver.observe(card);
});

// 概览卡片动画
const overviewObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry, index) => {
        if (entry.isIntersecting) {
            setTimeout(() => {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0) scale(1)';
            }, index * 100);
        }
    });
}, { threshold: 0.2 });

document.querySelectorAll('.overview-card').forEach(card => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px) scale(0.95)';
    card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    overviewObserver.observe(card);
});

// 步骤指示器动画
const stepObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry, index) => {
        if (entry.isIntersecting) {
            setTimeout(() => {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }, index * 100);
        }
    });
}, { threshold: 0.3 });

document.querySelectorAll('.step-item').forEach(step => {
    step.style.opacity = '0';
    step.style.transform = 'translateY(20px)';
    step.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    stepObserver.observe(step);
});

// 图表动画
const chartObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const chartItems = entry.target.querySelectorAll('.chart-item');
            chartItems.forEach((item, index) => {
                setTimeout(() => {
                    item.style.opacity = '1';
                    item.style.transform = `translate(-50%, -50%) rotate(${item.style.getPropertyValue('--angle')}) translateY(-150px) scale(1)`;
                }, index * 200);
            });
        }
    });
}, { threshold: 0.3 });

const distChart = document.querySelector('.dist-chart');
if (distChart) {
    distChart.querySelectorAll('.chart-item').forEach(item => {
        item.style.opacity = '0';
        item.style.transform = `translate(-50%, -50%) rotate(${item.style.getPropertyValue('--angle')}) translateY(-150px) scale(0.5)`;
        item.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    });
    chartObserver.observe(distChart);
}

// 移动端菜单切换
const mobileMenuToggle = document.getElementById('mobileMenuToggle');
const navMenu = document.querySelector('.nav-menu');

if (mobileMenuToggle) {
    mobileMenuToggle.addEventListener('click', () => {
        navMenu.classList.toggle('active');
        mobileMenuToggle.classList.toggle('active');
    });
}

// 鼠标跟随效果（可选）- 仅应用于概览卡片和特点卡片
document.addEventListener('mousemove', (e) => {
    const cards = document.querySelectorAll('.overview-card, .feature-card');
    cards.forEach(card => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        if (x >= 0 && x <= rect.width && y >= 0 && y <= rect.height) {
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            const rotateX = (y - centerY) / 20;
            const rotateY = (centerX - x) / 20;
            
            card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-8px)`;
        }
    });
});

// 重置卡片变换
document.addEventListener('mouseleave', (e) => {
    const target = e.target;
    if (!(target instanceof Element)) return;

    if (target.classList.contains('overview-card') || 
        target.classList.contains('feature-card')) {
        target.style.transform = '';
    }
});

// 页面加载动画
window.addEventListener('load', () => {
    document.body.style.opacity = '0';
    setTimeout(() => {
        document.body.style.transition = 'opacity 0.5s ease';
        document.body.style.opacity = '1';
    }, 100);
});

// 主题步骤指示器：滚动吸顶（始终保持在顶部可视）
const themesSteps = document.getElementById('themesSteps');
const themesStepsWrap = document.getElementById('themesStepsWrap');
const topNavbar = document.getElementById('navbar');

if (themesSteps && themesStepsWrap) {
    let isFloating = false;

    const getTopOffset = () => {
        const navbarHeight = topNavbar ? topNavbar.offsetHeight : 72;
        return navbarHeight + 4;
    };

    const getHeaderStackOffset = () => {
        // 预留：导航栏 + 吸顶步骤条 + 间距，避免遮住目标标题
        const navbarHeight = topNavbar ? topNavbar.offsetHeight : 72;
        const stepsHeight = themesSteps ? themesSteps.offsetHeight : 0;
        return navbarHeight + stepsHeight + 24;
    };

    const scrollToTheme = (themeId) => {
        if (!themeId) return;
        const target = document.getElementById(themeId);
        if (!target) return;

        const offset = getHeaderStackOffset();
        const targetTop = target.getBoundingClientRect().top + window.scrollY - offset;

        window.scrollTo({
            top: Math.max(0, targetTop),
            behavior: 'smooth'
        });
    };

    const applyFloatingState = () => {
        const topOffset = getTopOffset();
        themesSteps.style.setProperty('--steps-top', `${topOffset}px`);

        const wrapRect = themesStepsWrap.getBoundingClientRect();
        const shouldFloat = wrapRect.top <= topOffset;

        if (shouldFloat && !isFloating) {
            isFloating = true;
            themesSteps.classList.add('is-floating');
            themesStepsWrap.style.height = `${themesSteps.offsetHeight}px`;
        } else if (!shouldFloat && isFloating) {
            isFloating = false;
            themesSteps.classList.remove('is-floating');
            themesStepsWrap.style.height = '';
            themesSteps.style.removeProperty('--steps-top');
        } else if (shouldFloat && isFloating) {
            // 处理 resize / 字体加载导致高度变化
            themesStepsWrap.style.height = `${themesSteps.offsetHeight}px`;
        }
    };

    window.addEventListener('scroll', applyFloatingState, { passive: true });
    window.addEventListener('resize', applyFloatingState);
    applyFloatingState();

    // 点击步骤：跳转到对应主题板块（clothes/food/living/travel）
    themesSteps.querySelectorAll('.step-item').forEach((item) => {
        item.setAttribute('role', 'button');
        item.setAttribute('tabindex', '0');

        const themeId = item.getAttribute('data-theme');

        item.addEventListener('click', () => scrollToTheme(themeId));
        item.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                scrollToTheme(themeId);
            }
        });
    });
}

// 滚动进度指示器（可选）
let scrollProgress = document.createElement('div');
scrollProgress.className = 'scroll-progress';
scrollProgress.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    height: 4px;
    background: linear-gradient(90deg, #6366f1, #ec4899, #f59e0b);
    z-index: 9999;
    pointer-events: none;
    transform-origin: left;
    width: 0%;
    transition: width 0.1s ease;
`;
document.body.appendChild(scrollProgress);

window.addEventListener('scroll', () => {
    const windowHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    const scrolled = (window.scrollY / windowHeight) * 100;
    scrollProgress.style.width = scrolled + '%';
});

// 图片预览弹层
const lightbox = document.getElementById('imageLightbox');
const lightboxImage = document.getElementById('lightboxImage');

const openLightbox = (src, alt) => {
    if (!lightbox || !lightboxImage) return;
    lightboxImage.src = src;
    lightboxImage.alt = alt || '图片预览';
    lightbox.classList.add('is-open');
    lightbox.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
};

const closeLightbox = () => {
    if (!lightbox) return;
    lightbox.classList.remove('is-open');
    lightbox.setAttribute('aria-hidden', 'true');
    lightboxImage.src = '';
    document.body.style.overflow = '';
};

if (lightbox) {
    lightbox.addEventListener('click', (event) => {
        if (event.target.hasAttribute('data-lightbox-close')) {
            closeLightbox();
        }
    });
}

document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && lightbox?.classList.contains('is-open')) {
        closeLightbox();
    }
});

document.querySelectorAll('.character-images img, .pet-images img').forEach((img) => {
    img.style.cursor = 'zoom-in';
    img.addEventListener('click', () => {
        if (img.src) {
            openLightbox(img.src, img.alt);
        }
    });
});

// 手机端剧集目录下拉菜单
const sidebarToggle = document.getElementById('sidebarToggle');
const foodSidebar = sidebarToggle ? sidebarToggle.closest('.food-showcase-sidebar') : null;

if (sidebarToggle && foodSidebar) {
    // 三态循环: partial → open → closed → partial
    sidebarToggle.addEventListener('click', () => {
        if (foodSidebar.classList.contains('is-partial')) {
            foodSidebar.classList.remove('is-partial');
            foodSidebar.classList.add('is-open');
        } else if (foodSidebar.classList.contains('is-open')) {
            foodSidebar.classList.remove('is-open');
        } else {
            foodSidebar.classList.add('is-partial');
        }
    });
}

// 食篇剧集目录切换视频（预加载所有剧集）
const episodeList = document.getElementById('episodeList');
const playerContainer = document.getElementById('foodShowcasePlayer');

if (episodeList && playerContainer) {
    const episodes = episodeList.querySelectorAll('.showcase-episode-item');
    const descEl = document.getElementById('foodShowcaseDesc');
    const videoMap = new Map();
    let activeVideo = null;

    const isMobile = () => window.innerWidth <= 768;

    const updateMobileNames = () => {
        if (!isMobile()) return;
        episodes.forEach(item => {
            const nameEl = item.querySelector('.episode-name');
            const desc = item.getAttribute('data-desc');
            if (nameEl && desc) {
                nameEl.setAttribute('data-original', nameEl.getAttribute('data-original') || nameEl.textContent);
                nameEl.textContent = desc;
            }
        });
    };

    const restoreDesktopNames = () => {
        episodes.forEach(item => {
            const nameEl = item.querySelector('.episode-name');
            const original = nameEl ? nameEl.getAttribute('data-original') : null;
            if (nameEl && original) {
                nameEl.textContent = original;
            }
        });
    };

    const handleResize = () => {
        if (isMobile()) updateMobileNames();
        else restoreDesktopNames();
    };

    updateMobileNames();
    window.addEventListener('resize', handleResize);

    episodes.forEach((item) => {
        const src = item.getAttribute('data-video');
        if (!src) return;

        const video = document.createElement('video');
        video.className = 'food-showcase-video';
        video.controls = true;
        video.preload = 'auto';
        video.playsInline = true;
        video.src = src;
        video.style.display = 'none';
        playerContainer.appendChild(video);
        videoMap.set(src, video);

        if (item.classList.contains('is-active')) {
            video.style.display = '';
            activeVideo = video;
        }
    });

    episodeList.addEventListener('click', (e) => {
        const item = e.target.closest('.showcase-episode-item');
        if (!item || item.classList.contains('is-active')) return;

        const videoSrc = item.getAttribute('data-video');
        const nextVideo = videoMap.get(videoSrc);
        if (!nextVideo) return;

        episodes.forEach(el => el.classList.remove('is-active'));
        item.classList.add('is-active');

        if (descEl) {
            descEl.textContent = item.getAttribute('data-desc') || '';
        }

        if (activeVideo) {
            activeVideo.pause();
            activeVideo.style.display = 'none';
        }

        nextVideo.style.display = '';
        nextVideo.currentTime = 0;
        nextVideo.play().catch(() => {});
        activeVideo = nextVideo;

        if (foodSidebar) {
            foodSidebar.classList.remove('is-open');
            foodSidebar.classList.add('is-partial');
        }
    });
}

// 资产库链接兼容处理
// Mac 下不拦截点击，只在页面加载时把 href 改成 Mac 挂载路径，让浏览器原生跳转
const assetLibraryLink = document.getElementById('assetLibraryLink');
if (assetLibraryLink) {
    const isMacDesktop = /Macintosh|Mac OS X/i.test(navigator.userAgent) && !/iPhone|iPad|iPod/i.test(navigator.userAgent);
    
    // 仅在 file: 协议下启用 Mac 路径修正；HTTP 服务下使用默认相对路径即可
    if (isMacDesktop && window.location.protocol === 'file:') {
        assetLibraryLink.href = 'file:///Volumes/172.27.109.10/tmp/WuYiXiang/wuyixiang/Asset/%E8%A7%92%E8%89%B2%E5%BA%93.html';
    }
}
