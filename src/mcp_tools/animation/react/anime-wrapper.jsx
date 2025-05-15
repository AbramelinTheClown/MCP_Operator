import React, { useRef, useEffect } from 'react';
import { createSecureTimeline } from '../core-timeline';

const MCPAnimation = ({ children, targets, config }) => {
  const containerRef = useRef();
  const shadowRoot = useRef();

  useEffect(() => {
    if (!shadowRoot.current) {
      shadowRoot.current = containerRef.current.attachShadow({ mode: 'closed' });
    }

    const clone = document.createElement('div');
    clone.appendChild(children);
    shadowRoot.current.innerHTML = '';
    shadowRoot.current.appendChild(clone);

    const tl = createSecureTimeline({
      targets: shadowRoot.current.querySelectorAll(targets),
      ...config
    });

    return () => tl.pause();
  }, [targets, config]);

  return <div ref={containerRef} style={{ display: 'contents' }} />;
};

export default MCPAnimation;