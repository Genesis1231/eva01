import { useEffect } from 'react';
import '../styles/globals.css';

function MyApp({ Component, pageProps }) {
  // Add a check to ensure we're running on the client side
  useEffect(() => {
    // This will only run on the client side
    if (typeof window !== 'undefined') {
      console.log('React EVA Web Interface loaded');
    }
  }, []);

  return <Component {...pageProps} />;
}

export default MyApp; 