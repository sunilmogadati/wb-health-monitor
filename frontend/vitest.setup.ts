import "@testing-library/jest-dom/vitest";

// jsdom has no ResizeObserver; Recharts' ResponsiveContainer needs one to measure its box.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(globalThis as any).ResizeObserver = ResizeObserverStub;

// jsdom reports 0x0 for every element, so Recharts' ResponsiveContainer never gets a usable size.
Object.defineProperty(HTMLElement.prototype, "offsetWidth", { configurable: true, value: 600 });
Object.defineProperty(HTMLElement.prototype, "offsetHeight", { configurable: true, value: 400 });
