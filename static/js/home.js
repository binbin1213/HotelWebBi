// 主页动态效果
document.addEventListener('DOMContentLoaded', function() {
    // 数据统计数字动画
    const statElements = document.querySelectorAll('.animated-stat');
    
    if (statElements.length > 0) {
        const animateStats = () => {
            statElements.forEach(element => {
                const target = parseInt(element.getAttribute('data-target'));
                const duration = 1500; // 动画持续时间（毫秒）- 缩短为1.5秒
                const startTime = Date.now();
                const prefix = element.getAttribute('data-prefix') || '';
                const suffix = element.getAttribute('data-suffix') || '';
                
                const updateCount = () => {
                    const currentTime = Date.now();
                    const progress = Math.min((currentTime - startTime) / duration, 1);
                    const easeProgress = 1 - Math.pow(1 - progress, 3); // 缓动函数
                    const currentValue = Math.floor(target * easeProgress);
                    
                    element.textContent = prefix + currentValue.toLocaleString() + suffix;
                    
                    if (progress < 1) {
                        requestAnimationFrame(updateCount);
                    }
                };
                
                updateCount();
            });
        };
        
        // 创建观察器，当元素进入视口时开始动画
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateStats();
                    observer.disconnect(); // 只触发一次动画
                }
            });
        }, { threshold: 0.1 });
        
        // 观察第一个统计元素
        observer.observe(statElements[0]);
    }
    
    // 卡片淡入动画
    const cards = document.querySelectorAll('.card-hover');
    
    if (cards.length > 0) {
        const cardObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in-up');
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });
        
        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'opacity 0.5s ease, transform 0.5s ease'; // 加快过渡时间
            card.style.transitionDelay = `${index * 0.08}s`; // 减少延迟时间
            cardObserver.observe(card);
        });
    }
    
    // 特点部分动画
    const features = document.querySelectorAll('.feature-item');
    
    if (features.length > 0) {
        const featureObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateX(0)';
                }
            });
        }, { threshold: 0.1 });
        
        features.forEach((feature, index) => {
            feature.style.opacity = '0';
            feature.style.transform = index % 2 === 0 ? 'translateX(-15px)' : 'translateX(15px)'; // 减小位移距离
            feature.style.transition = 'opacity 0.5s ease, transform 0.5s ease'; // 加快过渡时间
            feature.style.transitionDelay = `${index * 0.08}s`; // 减少延迟时间
            featureObserver.observe(feature);
        });
    }
    
    // 英雄区域文字动画 - 更快的动画效果
    const heroText = document.querySelector('.hero-text');
    const heroSubtext = document.querySelector('.hero-subtext');
    
    if (heroText && heroSubtext) {
        // 立即开始动画，减少延迟
        setTimeout(() => {
            heroText.style.opacity = '1';
            heroText.style.transform = 'translateY(0)';
            
            setTimeout(() => {
                heroSubtext.style.opacity = '1';
                heroSubtext.style.transform = 'translateY(0)';
            }, 200); // 减少子标题动画延迟
        }, 50); // 减少主标题动画延迟
    }
}); 