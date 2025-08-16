import React from 'react';
import styles from './LoadingSpinner.module.css';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  className?: string;
  label?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'medium',
  className,
  label = 'Loading...',
}) => {
  return (
    <div 
      className={`${styles.spinner} ${styles[size]} ${className || ''}`}
      role="status"
      aria-label={label}
    >
      <div className={styles.spinnerCircle}></div>
      <span className={styles.srOnly}>{label}</span>
    </div>
  );
};
