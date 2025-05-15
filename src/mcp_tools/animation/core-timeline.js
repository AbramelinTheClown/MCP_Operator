import { timeline } from 'animejs/lib/anime.es.js';

const SECURITY = {
  MAX_DURATION: 5000,
  ALLOWED_CSS_VARS: ['--mcp-animation-progress', '--mcp-timeline-state']
};

export const createSecureTimeline = (targets) => {
  const tl = timeline({
    duration: 750,
    easing: 'easeOutExpo',
    update: () => {
      // Security: Validate animation state on each frame
      if (tl.duration > SECURITY.MAX_DURATION) {
        tl.pause();
        console.warn('Animation duration exceeded security limits');
      }
    }
  });

  // Validate CSS variables before applying
  const sanitizedTargets = targets.map(target => ({
    ...target,
    cssVar: Object.keys(target.cssVar || {}).reduce((acc, key) => {
      if (SECURITY.ALLOWED_CSS_VARS.includes(key)) {
        acc[key] = target.cssVar[key];
      }
      return acc;
    }, {})
  }));

  return tl.add(sanitizedTargets);
};