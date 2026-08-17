/* ══════════════════════════════════════════════════════════════════
   Dawrha — Image Carousel controller
   JS-driven: toggles .is-active, updates dots, autoplay + pause-on-hover,
   prev/next arrows, keyboard arrows, and full accessibility.
   Supports multiple carousels on one page.
   ==================================================================== */
(function () {
    'use strict';

    var AUTOPLAY_MS = 4500;   // must match the dwProgress animation duration

    function ImageCarousel(container) {
        this.container = container;
        this.images = Array.prototype.slice.call(
            container.querySelectorAll('.carousel-image'));
        this.dots = Array.prototype.slice.call(
            container.querySelectorAll('.carousel-dots .dot'));
        this.prevBtn = container.querySelector('.carousel-prev');
        this.nextBtn = container.querySelector('.carousel-next');
        this.index = 0;
        this.count = this.images.length;
        this.timer = null;
        if (this.count > 0) {
            this.init();
        }
    }

    ImageCarousel.prototype.init = function () {
        var self = this;

        // Accessibility on the container.
        this.container.setAttribute('role', 'region');
        this.container.setAttribute('aria-roledescription', 'carousel');
        if (!this.container.getAttribute('aria-label')) {
            this.container.setAttribute('aria-label', 'Image carousel');
        }

        // Arrows.
        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', function () { self.prev(true); });
        }
        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', function () { self.next(true); });
        }

        // Dots.
        this.dots.forEach(function (dot, i) {
            dot.setAttribute('role', 'button');
            dot.setAttribute('tabindex', '0');
            dot.setAttribute('aria-label', 'Go to image ' + (i + 1));
            dot.addEventListener('click', function () { self.goTo(i, true); });
            dot.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    self.goTo(i, true);
                }
            });
        });

        // Pause on hover / focus.
        this.container.addEventListener('mouseenter', function () { self.stop(); });
        this.container.addEventListener('mouseleave', function () { self.start(); });
        this.container.addEventListener('focusin', function () { self.stop(); });
        this.container.addEventListener('focusout', function () { self.start(); });

        // Keyboard arrows (only when this carousel is hovered/focused, and not
        // while typing in a form field — so we never hijack the user's input).
        this._onKey = function (e) {
            var active = document.activeElement;
            if (active && /^(INPUT|TEXTAREA|SELECT)$/.test(active.tagName)) return;
            if (!self.container.matches(':hover') && !self.container.contains(active)) return;
            if (e.key === 'ArrowLeft') { e.preventDefault(); self.prev(true); }
            else if (e.key === 'ArrowRight') { e.preventDefault(); self.next(true); }
        };
        document.addEventListener('keydown', this._onKey);

        // Autoplay progress bar (injected so templates stay unchanged).
        var wrapper = this.container.querySelector('.carousel-wrapper');
        if (wrapper && !wrapper.querySelector('.carousel-progress')) {
            var prog = document.createElement('div');
            prog.className = 'carousel-progress';
            prog.appendChild(document.createElement('span'));
            wrapper.appendChild(prog);
        }
        this._bar = wrapper ? wrapper.querySelector('.carousel-progress span') : null;

        // Respect reduced-motion: still cycle, just no manual fuss.
        this.render();
        this.start();
    };

    // Restart (or clear) the progress-bar fill animation.
    ImageCarousel.prototype._progress = function (running) {
        if (!this._bar) return;
        this._bar.classList.remove('run');
        void this._bar.offsetWidth;      // reflow → restart the CSS animation
        if (running) this._bar.classList.add('run');
    };

    ImageCarousel.prototype.render = function () {
        var self = this;
        this.images.forEach(function (img, i) {
            var on = i === self.index;
            img.classList.toggle('is-active', on);
            img.setAttribute('aria-hidden', on ? 'false' : 'true');
        });
        this.dots.forEach(function (dot, i) {
            var on = i === self.index;
            dot.classList.toggle('active', on);
            dot.setAttribute('aria-current', on ? 'true' : 'false');
        });
    };

    ImageCarousel.prototype.goTo = function (i, restart) {
        this.index = ((i % this.count) + this.count) % this.count;
        this.render();
        if (restart) this.start();      // reset the autoplay timer after manual nav
        else this._progress(!!this.timer);
    };

    ImageCarousel.prototype.next = function (restart) { this.goTo(this.index + 1, restart); };
    ImageCarousel.prototype.prev = function (restart) { this.goTo(this.index - 1, restart); };

    ImageCarousel.prototype.start = function () {
        var self = this;
        this.stop();
        if (this.count <= 1) return;
        this.timer = setInterval(function () { self.next(false); }, AUTOPLAY_MS);
        this._progress(true);
    };

    ImageCarousel.prototype.stop = function () {
        if (this.timer) { clearInterval(this.timer); this.timer = null; }
        this._progress(false);
    };

    function initAll() {
        var nodes = document.querySelectorAll('.image-carousel-container');
        for (var i = 0; i < nodes.length; i++) {
            if (!nodes[i]._dwCarousel) {
                nodes[i]._dwCarousel = new ImageCarousel(nodes[i]);
            }
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAll);
    } else {
        initAll();
    }
    // Expose for pages that inject carousels after load.
    window.dwInitCarousels = initAll;
})();
