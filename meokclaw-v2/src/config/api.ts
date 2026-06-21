// API configuration for web and mobile
export const API_CONFIG = {
  // Default for local development
  localBase: "http://localhost:3201",
  
  // For mobile apps connecting to the dev machine
  // Update this to your machine's IP address
  mobileBase: "http://192.168.50.105:3201",
  
  // Auto-detect based on environment
  getBaseUrl(): string {
    if (typeof window === "undefined") return this.localBase;
    
    // Capacitor / mobile environment
    const isMobile = /Capacitor|Android|iPhone|iPad/i.test(navigator.userAgent);
    if (isMobile) return this.mobileBase;
    
    // LAN access (not localhost)
    if (window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
      return `http://${window.location.hostname}:3201`;
    }
    
    return this.localBase;
  }
};
