/**
 * Date Utilities - Berlin Timezone (Europe/Berlin) with automatic DST handling
 */

/**
 * Format a timestamp to Berlin timezone
 * @param {string|Date|number} timestamp - ISO string, Date object, or timestamp
 * @param {object} options - Intl.DateTimeFormat options
 * @returns {string} Formatted date/time string in Berlin timezone
 */
export const formatBerlinTime = (timestamp, options = {}) => {
  try {
    const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
    
    if (isNaN(date.getTime())) {
      return "";
    }
    
    const defaultOptions = {
      timeZone: "Europe/Berlin",
      ...options
    };
    
    return date.toLocaleString("de-DE", defaultOptions);
  } catch (error) {
    console.error("Error formatting Berlin time:", error);
    return "";
  }
};

/**
 * Format time only (HH:mm) in Berlin timezone
 * @param {string|Date|number} timestamp - ISO string, Date object, or timestamp
 * @returns {string} Formatted time string (HH:mm) in Berlin timezone
 */
export const formatBerlinTimeOnly = (timestamp) => {
  return formatBerlinTime(timestamp, {
    hour: "2-digit",
    minute: "2-digit"
  });
};

/**
 * Format date and time in Berlin timezone
 * @param {string|Date|number} timestamp - ISO string, Date object, or timestamp
 * @returns {string} Formatted date and time string in Berlin timezone
 */
export const formatBerlinDateTime = (timestamp) => {
  return formatBerlinTime(timestamp, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
};

/**
 * Format date only in Berlin timezone
 * @param {string|Date|number} timestamp - ISO string, Date object, or timestamp
 * @returns {string} Formatted date string in Berlin timezone
 */
export const formatBerlinDate = (timestamp) => {
  return formatBerlinTime(timestamp, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  });
};

/**
 * Get current timestamp in Berlin timezone as ISO string
 * @returns {string} Current date/time as ISO string in UTC
 */
export const getCurrentBerlinTimestamp = () => {
  return new Date().toISOString();
};

