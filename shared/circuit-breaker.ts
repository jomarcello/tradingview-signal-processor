import { CircuitBreaker } from 'opossum';

export function createCircuitBreaker(asyncFn: Function) {
  return new CircuitBreaker(asyncFn, {
    timeout: 3000,
    errorThresholdPercentage: 50,
    resetTimeout: 30000
  });
} 